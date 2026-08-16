"""Administrative management APIs.

These routes are intentionally separate from learner-facing read APIs.  Every
endpoint requires an explicit RBAC permission and returns only operational data
needed by the administration console.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import current_user, require_permissions
from app.models.entities import (
    AuditLog, Coupon, CurrentAffairs, Payment, Question, Role, Subscription,
    Setting, SubscriptionPlan, Taxonomy, Test, TestAttempt, TestQuestion, User, UserRole,
)
from app.schemas.mobile import TestCreate

router = APIRouter(prefix="/admin", tags=["Administration"])


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    status: str | None = Field(default=None, pattern="^(active|inactive|suspended)$")
    is_verified: bool | None = None


class RoleInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    permissions: list[str] = Field(default_factory=list)


class StatusInput(BaseModel):
    status: str = Field(pattern="^(active|inactive|draft|approved|rejected|archived)$")


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price_paise: int | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, gt=0)
    test_limit: int | None = Field(default=None, ge=1)
    includes_video: bool | None = None
    all_access: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")


class CouponUpdate(BaseModel):
    discount_percent: int | None = Field(default=None, ge=1, le=100)
    valid_until: datetime | None = None
    max_uses: int | None = Field(default=None, ge=1)
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")


class CurrentAffairsUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    body: str | None = Field(default=None, min_length=1)
    published_at: datetime | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")


def page_meta(page: int, size: int, total: int) -> dict:
    return {"page": page, "size": size, "total": total, "pages": (total + size - 1) // size}


def soft_delete(item, actor_id: uuid.UUID) -> None:
    item.deleted_at = datetime.now(UTC)
    item.updated_by = actor_id


@router.get("/users", dependencies=[Depends(require_permissions("admin:read"))])
async def users(search: str | None = None, user_status: str | None = Query(None, alias="status"), page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.deleted_at.is_(None))
    if search:
        query = query.where(or_(User.email.ilike(f"%{search}%"), User.phone.ilike(f"%{search}%"), User.display_name.ilike(f"%{search}%")))
    if user_status:
        query = query.where(User.status == user_status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.scalars(query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size))).all()
    return {"data": [{"id": str(x.id), "email": x.email, "phone": x.phone, "display_name": x.display_name, "status": x.status, "is_verified": x.is_verified, "created_at": x.created_at} for x in rows], "meta": page_meta(page, size, total or 0)}


@router.get("/users/{user_id}", dependencies=[Depends(require_permissions("admin:read"))])
async def user_detail(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user or user.deleted_at: raise HTTPException(404, "User not found")
    roles = (await db.scalars(select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id, UserRole.deleted_at.is_(None)))).all()
    subscriptions = (await db.scalars(select(Subscription).where(Subscription.user_id == user.id, Subscription.deleted_at.is_(None)).order_by(Subscription.ends_at.desc()))).all()
    return {"data": {"id": str(user.id), "email": user.email, "phone": user.phone, "display_name": user.display_name, "status": user.status, "is_verified": user.is_verified, "roles": list(roles), "subscriptions": [{"id": str(x.id), "plan_id": str(x.plan_id), "starts_at": x.starts_at, "ends_at": x.ends_at, "tests_used": x.tests_used} for x in subscriptions]}}


@router.patch("/users/{user_id}", dependencies=[Depends(require_permissions("admin:write"))])
async def update_user(user_id: uuid.UUID, payload: UserUpdate, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user or user.deleted_at: raise HTTPException(404, "User not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(user, key, value)
    user.updated_by = actor.id; await db.commit()
    return {"message": "User updated"}


@router.get("/roles", dependencies=[Depends(require_permissions("admin:read"))])
async def roles(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Role).where(Role.deleted_at.is_(None)).order_by(Role.name))).all()
    return {"data": [{"id": str(x.id), "name": x.name, "permissions": x.permissions, "status": x.status} for x in rows]}


@router.post("/roles", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("admin:write"))])
async def create_role(payload: RoleInput, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(Role.id).where(Role.name == payload.name, Role.deleted_at.is_(None))): raise HTTPException(409, "Role already exists")
    role = Role(**payload.model_dump(), created_by=actor.id, updated_by=actor.id); db.add(role); await db.commit()
    return {"data": {"id": str(role.id)}}


@router.patch("/roles/{role_id}", dependencies=[Depends(require_permissions("admin:write"))])
async def update_role(role_id: uuid.UUID, payload: RoleInput, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    role = await db.get(Role, role_id)
    if not role or role.deleted_at: raise HTTPException(404, "Role not found")
    role.name, role.permissions, role.updated_by = payload.name, payload.permissions, actor.id; await db.commit()
    return {"message": "Role updated"}


@router.delete("/roles/{role_id}", status_code=204, dependencies=[Depends(require_permissions("admin:write"))])
async def delete_role(role_id: uuid.UUID, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    role = await db.get(Role, role_id)
    if not role or role.deleted_at: raise HTTPException(404, "Role not found")
    soft_delete(role, actor.id); await db.commit()


@router.put("/users/{user_id}/roles/{role_id}", dependencies=[Depends(require_permissions("admin:write"))])
async def assign_role(user_id: uuid.UUID, role_id: uuid.UUID, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if not await db.get(User, user_id) or not await db.get(Role, role_id): raise HTTPException(404, "User or role not found")
    assignment = await db.scalar(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id))
    if not assignment: db.add(UserRole(user_id=user_id, role_id=role_id, created_by=actor.id, updated_by=actor.id)); await db.commit()
    return {"message": "Role assigned"}


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204, dependencies=[Depends(require_permissions("admin:write"))])
async def unassign_role(user_id: uuid.UUID, role_id: uuid.UUID, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    assignment = await db.scalar(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id, UserRole.deleted_at.is_(None)))
    if not assignment: raise HTTPException(404, "Role assignment not found")
    soft_delete(assignment, actor.id); await db.commit()


@router.get("/questions/{question_id}", dependencies=[Depends(require_permissions("questions:write"))])
async def question_detail(question_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    question = await db.get(Question, question_id)
    if not question or question.deleted_at: raise HTTPException(404, "Question not found")
    return {"data": {key: (str(value) if isinstance(value, uuid.UUID) else value) for key, value in {"id": question.id, "exam_id": question.exam_id, "subject_id": question.subject_id, "topic_id": question.topic_id, "body": question.body, "options": question.options, "answer": question.answer, "explanation": question.explanation, "difficulty": question.difficulty, "question_type": question.question_type, "marks": question.marks, "negative_marks": question.negative_marks, "approval_status": question.approval_status}.items()}}


@router.get("/questions", dependencies=[Depends(require_permissions("questions:write"))])
async def admin_questions(search: str | None = None, approval_status: str | None = None, page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    """Paginated moderation queue; use approval_status=draft for pending items."""
    query = select(Question).where(Question.deleted_at.is_(None))
    if search:
        query = query.where(Question.body.ilike(f"%{search}%"))
    if approval_status:
        query = query.where(Question.approval_status == approval_status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.scalars(query.order_by(Question.created_at.desc()).offset((page - 1) * size).limit(size))).all()
    return {"data": [{"id": str(x.id), "body": x.body, "exam_id": str(x.exam_id), "subject_id": str(x.subject_id) if x.subject_id else None, "topic_id": str(x.topic_id) if x.topic_id else None, "difficulty": x.difficulty, "question_type": x.question_type, "approval_status": x.approval_status, "created_at": x.created_at} for x in rows], "meta": page_meta(page, size, total or 0)}


@router.patch("/questions/{question_id}/approval", dependencies=[Depends(require_permissions("questions:write"))])
async def moderate_question(question_id: uuid.UUID, payload: StatusInput, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    question = await db.get(Question, question_id)
    if not question or question.deleted_at: raise HTTPException(404, "Question not found")
    if payload.status not in {"draft", "approved", "rejected", "archived"}: raise HTTPException(422, "Invalid question approval status")
    question.approval_status, question.updated_by = payload.status, actor.id; await db.commit()
    return {"message": "Question moderation status updated"}


@router.get("/tests", dependencies=[Depends(require_permissions("content:write"))])
async def tests(search: str | None = None, test_status: str | None = Query(None, alias="status"), page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    query = select(Test).where(Test.deleted_at.is_(None))
    if search:
        query = query.where(or_(Test.title.ilike(f"%{search}%"), Test.description.ilike(f"%{search}%")))
    if test_status:
        query = query.where(Test.status == test_status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.scalars(query.order_by(Test.created_at.desc()).offset((page - 1) * size).limit(size))).all()
    return {"data": [{"id": str(x.id), "title": x.title, "test_type": x.test_type, "quiz_type": x.quiz_type, "duration_minutes": x.duration_minutes, "status": x.status, "starts_at": x.starts_at, "ends_at": x.ends_at} for x in rows], "meta": page_meta(page, size, total or 0)}


@router.patch("/tests/{test_id}", dependencies=[Depends(require_permissions("content:write"))])
async def update_test(test_id: uuid.UUID, payload: TestCreate, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    test = await db.get(Test, test_id)
    if not test or test.deleted_at: raise HTTPException(404, "Test not found")
    if payload.test_type == "live" and (not payload.starts_at or not payload.ends_at): raise HTTPException(422, "Live tests require starts_at and ends_at")
    for key, value in payload.model_dump(exclude={"question_ids"}).items(): setattr(test, key, value)
    test.resume_allowed, test.updated_by = payload.test_type != "live", actor.id
    old = (await db.scalars(select(TestQuestion).where(TestQuestion.test_id == test.id, TestQuestion.deleted_at.is_(None)))).all()
    for row in old: soft_delete(row, actor.id)
    db.add_all([TestQuestion(test_id=test.id, question_id=qid, sequence=index, created_by=actor.id, updated_by=actor.id) for index, qid in enumerate(payload.question_ids, 1)])
    await db.commit(); return {"message": "Test updated"}


@router.delete("/tests/{test_id}", status_code=204, dependencies=[Depends(require_permissions("content:write"))])
async def delete_test(test_id: uuid.UUID, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    test = await db.get(Test, test_id)
    if not test or test.deleted_at: raise HTTPException(404, "Test not found")
    soft_delete(test, actor.id); await db.commit()


@router.get("/plans", dependencies=[Depends(require_permissions("subscriptions:write"))])
async def admin_plans(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.deleted_at.is_(None)).order_by(SubscriptionPlan.created_at.desc()))).all()
    return {"data": [{"id": str(x.id), "name": x.name, "price_paise": x.price_paise, "duration_days": x.duration_days, "test_limit": x.test_limit, "includes_video": x.includes_video, "all_access": x.all_access, "status": x.status} for x in rows]}


@router.patch("/plans/{plan_id}", dependencies=[Depends(require_permissions("subscriptions:write"))])
async def update_plan(plan_id: uuid.UUID, payload: PlanUpdate, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.deleted_at: raise HTTPException(404, "Plan not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(plan, key, value)
    plan.updated_by = actor.id; await db.commit(); return {"message": "Plan updated"}


@router.delete("/plans/{plan_id}", status_code=204, dependencies=[Depends(require_permissions("subscriptions:write"))])
async def delete_plan(plan_id: uuid.UUID, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.deleted_at: raise HTTPException(404, "Plan not found")
    soft_delete(plan, actor.id); await db.commit()


@router.get("/coupons", dependencies=[Depends(require_permissions("subscriptions:write"))])
async def coupons(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Coupon).where(Coupon.deleted_at.is_(None)).order_by(Coupon.created_at.desc()))).all()
    return {"data": [{"id": str(x.id), "code": x.code, "discount_percent": x.discount_percent, "valid_until": x.valid_until, "max_uses": x.max_uses, "used_count": x.used_count, "status": x.status} for x in rows]}


@router.patch("/coupons/{coupon_id}", dependencies=[Depends(require_permissions("subscriptions:write"))])
async def update_coupon(coupon_id: uuid.UUID, payload: CouponUpdate, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    coupon = await db.get(Coupon, coupon_id)
    if not coupon or coupon.deleted_at: raise HTTPException(404, "Coupon not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(coupon, key, value)
    coupon.updated_by = actor.id; await db.commit(); return {"message": "Coupon updated"}


@router.delete("/coupons/{coupon_id}", status_code=204, dependencies=[Depends(require_permissions("subscriptions:write"))])
async def delete_coupon(coupon_id: uuid.UUID, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    coupon = await db.get(Coupon, coupon_id)
    if not coupon or coupon.deleted_at: raise HTTPException(404, "Coupon not found")
    soft_delete(coupon, actor.id); await db.commit()


@router.get("/settings", dependencies=[Depends(require_permissions("admin:read"))])
async def settings(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Setting).where(Setting.deleted_at.is_(None)).order_by(Setting.key))).all()
    return {"data": [{"key": x.key, "value": x.value_json, "updated_at": x.updated_at} for x in rows]}


@router.get("/current-affairs", dependencies=[Depends(require_permissions("content:write"))])
async def admin_current_affairs(search: str | None = None, item_status: str | None = Query(None, alias="status"), page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    query = select(CurrentAffairs).where(CurrentAffairs.deleted_at.is_(None))
    if search:
        query = query.where(or_(CurrentAffairs.title.ilike(f"%{search}%"), CurrentAffairs.body.ilike(f"%{search}%")))
    if item_status:
        query = query.where(CurrentAffairs.status == item_status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.scalars(query.order_by(CurrentAffairs.published_at.desc()).offset((page - 1) * size).limit(size))).all()
    return {"data": [{"id": str(x.id), "title": x.title, "body": x.body, "published_at": x.published_at, "status": x.status} for x in rows], "meta": page_meta(page, size, total or 0)}


@router.patch("/current-affairs/{item_id}", dependencies=[Depends(require_permissions("content:write"))])
async def update_current_affairs(item_id: uuid.UUID, payload: CurrentAffairsUpdate, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(CurrentAffairs, item_id)
    if not item or item.deleted_at: raise HTTPException(404, "Current-affairs item not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    item.updated_by = actor.id; await db.commit(); return {"message": "Current-affairs item updated"}


@router.delete("/current-affairs/{item_id}", status_code=204, dependencies=[Depends(require_permissions("content:write"))])
async def delete_current_affairs(item_id: uuid.UUID, actor: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    item = await db.get(CurrentAffairs, item_id)
    if not item or item.deleted_at: raise HTTPException(404, "Current-affairs item not found")
    soft_delete(item, actor.id); await db.commit()


@router.get("/payments", dependencies=[Depends(require_permissions("subscriptions:write"))])
async def payments(payment_status: str | None = Query(None, alias="status"), page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    query = select(Payment).where(Payment.deleted_at.is_(None))
    if payment_status: query = query.where(Payment.status == payment_status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.scalars(query.order_by(Payment.created_at.desc()).offset((page - 1) * size).limit(size))).all()
    return {"data": [{"id": str(x.id), "user_id": str(x.user_id), "plan_id": str(x.plan_id), "amount_paise": x.amount_paise, "status": x.status, "order_id": x.razorpay_order_id, "payment_id": x.razorpay_payment_id, "invoice_number": x.invoice_number, "created_at": x.created_at} for x in rows], "meta": page_meta(page, size, total or 0)}


@router.get("/audit-logs", dependencies=[Depends(require_permissions("admin:read"))])
async def audit_logs(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    query = select(AuditLog).where(AuditLog.deleted_at.is_(None)); total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.scalars(query.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size))).all()
    return {"data": [{"id": str(x.id), "actor_id": str(x.actor_id) if x.actor_id else None, "action": x.action, "resource": x.resource, "resource_id": x.resource_id, "metadata": x.metadata_json, "created_at": x.created_at} for x in rows], "meta": page_meta(page, size, total or 0)}


@router.get("/analytics", dependencies=[Depends(require_permissions("admin:read"))])
async def analytics(db: AsyncSession = Depends(get_db)):
    users = await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None), User.status == "active"))
    paid = await db.scalar(select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(Payment.status == "paid", Payment.deleted_at.is_(None)))
    attempts = await db.scalar(select(func.count(TestAttempt.id)).where(TestAttempt.deleted_at.is_(None)))
    submitted = await db.scalar(select(func.count(TestAttempt.id)).where(TestAttempt.status == "submitted", TestAttempt.deleted_at.is_(None)))
    return {"data": {"users": users, "active_users": active_users, "revenue_paise": paid, "attempts": attempts, "submitted_attempts": submitted}}


@router.get("/analytics/detailed", dependencies=[Depends(require_permissions("admin:read"))])
async def detailed_analytics(db: AsyncSession = Depends(get_db)):
    """Report-ready metrics; subject rankings are ordered by completed-test use."""
    current = datetime.now(UTC)
    revenue = await db.scalar(select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(Payment.status == "paid", Payment.deleted_at.is_(None)))
    active_subscriptions = await db.scalar(select(func.count(Subscription.id)).where(Subscription.deleted_at.is_(None), Subscription.status == "active", Subscription.ends_at > current))
    avg_time = await db.scalar(select(func.avg(func.extract("epoch", TestAttempt.submitted_at - TestAttempt.started_at))).where(TestAttempt.status == "submitted", TestAttempt.submitted_at.is_not(None), TestAttempt.deleted_at.is_(None)))
    ranking_rows = (await db.execute(
        select(
            Question.subject_id,
            Taxonomy.name.label("subject_name"),
            func.count(func.distinct(TestAttempt.id)).label("attempt_count"),
        )
        .join(Taxonomy, Taxonomy.id == Question.subject_id)
        .join(TestQuestion, TestQuestion.question_id == Question.id)
        .join(TestAttempt, TestAttempt.test_id == TestQuestion.test_id)
        .where(Question.deleted_at.is_(None), Question.subject_id.is_not(None), TestQuestion.deleted_at.is_(None), TestAttempt.deleted_at.is_(None), TestAttempt.status == "submitted")
        # PostgreSQL requires every selected non-aggregate column to be in the
        # grouping set.  Grouping only by ``Question.subject_id`` caused this
        # dashboard endpoint to return a 500 whenever the rankings query ran.
        .group_by(Question.subject_id, Taxonomy.name)
        .order_by(func.count(func.distinct(TestAttempt.id)).desc())
        .limit(10)
    )).all()
    average_test_time_seconds = round(float(avg_time or 0), 2)
    subject_rankings = [
        {
            "subject_id": str(row.subject_id),
            "subject_name": row.subject_name,
            "completed_attempts": row.attempt_count,
        }
        for row in ranking_rows
    ]
    return {"data": {
        "revenue": float((revenue or 0) / 100),
        "active_subscriptions": active_subscriptions or 0,
        "average_test_time_seconds": average_test_time_seconds,
        # Dashboard-friendly aliases retained alongside the explicit names.
        "active_subs": active_subscriptions or 0,
        "avg_time": average_test_time_seconds,
        "subject_rankings": subject_rankings,
    }}
