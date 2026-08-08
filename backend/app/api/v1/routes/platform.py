"""User, media, commerce, notification and administration API surface."""
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db
from app.dependencies.auth import current_user, require_permissions
from app.models.entities import (Coupon, CurrentAffairs, DeviceToken, Notification, Payment,
    Setting, Subscription, SubscriptionPlan, TestAttempt, User, Video)
from app.services.notifications import send_topic_notification

router = APIRouter(tags=["Platform"])

class ProfileUpdate(BaseModel): display_name: str = Field(min_length=1, max_length=160)
class DeviceInput(BaseModel): token: str = Field(min_length=20, max_length=512); platform: str = Field(pattern="^(android|ios|web)$")
class MediaInput(BaseModel): title: str; description: str | None = None; url: str; topic_id: uuid.UUID | None = None; is_free: bool = False
class PlanInput(BaseModel): name: str; price_paise: int = Field(ge=0); duration_days: int = Field(gt=0); test_limit: int | None = Field(default=None, ge=1); includes_video: bool = False; all_access: bool = False
class OrderInput(BaseModel): plan_id: uuid.UUID; coupon_code: str | None = None
class PaymentVerify(BaseModel): razorpay_order_id: str; razorpay_payment_id: str; razorpay_signature: str
class NotificationInput(BaseModel): title: str; body: str; data: dict[str, str] = {}
class CouponInput(BaseModel): code: str = Field(min_length=3, max_length=64); discount_percent: int = Field(ge=1, le=100); valid_until: datetime | None = None; max_uses: int | None = Field(default=None, ge=1)
class CurrentAffairsInput(BaseModel): title: str = Field(min_length=1, max_length=240); body: str = Field(min_length=1); published_at: datetime | None = None
class SettingInput(BaseModel): value: dict

def client() -> Any:
    # Import only when payment endpoints are invoked so non-payment API health
    # checks remain available even during an optional SDK packaging failure.
    import razorpay
    s = get_settings()
    if not s.razorpay_key_id or not s.razorpay_key_secret: raise HTTPException(503, "Payments are not configured")
    return razorpay.Client(auth=(s.razorpay_key_id, s.razorpay_key_secret))

@router.get("/users/me")
async def profile(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    subscription = await db.scalar(select(Subscription).where(Subscription.user_id == user.id, Subscription.ends_at > datetime.now(UTC), Subscription.status == "active").order_by(Subscription.ends_at.desc()))
    return {"data": {"id": str(user.id), "phone": user.phone, "email": user.email, "display_name": user.display_name, "subscription_expires_at": subscription.ends_at if subscription else None}}

@router.patch("/users/me")
async def update_profile(payload: ProfileUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    user.display_name = payload.display_name; await db.commit(); return {"message": "Profile updated"}

@router.get("/users/me/analytics")
async def user_analytics(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(TestAttempt).where(TestAttempt.user_id == user.id, TestAttempt.status == "submitted"))).all()
    score = sum(x.score for x in rows); total = sum(x.total_marks for x in rows)
    return {"data": {"tests_taken": len(rows), "score": score, "accuracy": round(score * 100 / total, 2) if total else 0, "study_seconds": sum(max(0, int(((x.submitted_at or datetime.now(UTC)) - x.started_at).total_seconds())) for x in rows)}}

@router.get("/users/me/rank")
async def user_rank(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Return an overall rank based on completed-test score, then time taken."""
    rows = (await db.execute(select(TestAttempt.user_id, func.sum(TestAttempt.score).label("score"), func.sum(TestAttempt.total_marks).label("total"), func.min(TestAttempt.submitted_at).label("submitted")).where(TestAttempt.status == "submitted").group_by(TestAttempt.user_id).order_by(func.sum(TestAttempt.score).desc(), func.min(TestAttempt.submitted_at).asc()))).all()
    rank = next((index for index, row in enumerate(rows, 1) if row.user_id == user.id), None)
    own = next((row for row in rows if row.user_id == user.id), None)
    return {"data": {"rank": rank, "participants": len(rows), "score": int(own.score) if own else 0, "total_marks": int(own.total) if own else 0}}

@router.post("/devices")
async def register_device(payload: DeviceInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    token = await db.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
    if token: token.user_id, token.platform = user.id, payload.platform
    else: db.add(DeviceToken(user_id=user.id, token=payload.token, platform=payload.platform, created_by=user.id, updated_by=user.id))
    await db.commit(); return {"message": "Device registered"}

@router.get("/videos")
async def videos(topic_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Video).where(Video.status == "active", Video.deleted_at.is_(None))
    if topic_id: q = q.where(Video.topic_id == topic_id)
    return {"data": [{"id": str(x.id), "title": x.title, "url": x.stream_url, "is_free": x.is_free} for x in (await db.scalars(q)).all()]}

@router.post("/admin/videos", dependencies=[Depends(require_permissions("content:write"))], status_code=201)
async def create_video(payload: MediaInput, bg: BackgroundTasks, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = Video(title=payload.title, description=payload.description, stream_url=payload.url, topic_id=payload.topic_id, is_free=payload.is_free, created_by=user.id, updated_by=user.id); db.add(item); await db.commit()
    bg.add_task(send_topic_notification, "New video uploaded", item.title, "video", str(item.id)); return {"data": {"id": str(item.id)}}

@router.put("/admin/videos/{video_id}", dependencies=[Depends(require_permissions("content:write"))])
async def update_video(video_id: uuid.UUID, payload: MediaInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(Video, video_id)
    if not item or item.deleted_at: raise HTTPException(404, "Video not found")
    item.title, item.description, item.stream_url, item.topic_id, item.is_free, item.updated_by = payload.title, payload.description, payload.url, payload.topic_id, payload.is_free, user.id
    await db.commit(); return {"message": "Video updated"}

@router.delete("/admin/videos/{video_id}", status_code=204, dependencies=[Depends(require_permissions("content:write"))])
async def delete_video(video_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    item = await db.get(Video, video_id)
    if not item or item.deleted_at: raise HTTPException(404, "Video not found")
    item.deleted_at, item.updated_by = datetime.now(UTC), user.id; await db.commit()

@router.get("/plans")
async def plans(db: AsyncSession = Depends(get_db)):
    return {"data": [{"id": str(x.id), "name": x.name, "price_paise": x.price_paise, "duration_days": x.duration_days, "test_limit": x.test_limit, "includes_video": x.includes_video, "all_access": x.all_access} for x in (await db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.status == "active"))).all()]}

@router.post("/admin/plans", dependencies=[Depends(require_permissions("subscriptions:write"))], status_code=201)
async def create_plan(payload: PlanInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    plan = SubscriptionPlan(**payload.model_dump(), created_by=user.id, updated_by=user.id); db.add(plan); await db.commit(); return {"data": {"id": str(plan.id)}}

@router.post("/payments/orders", status_code=201)
async def create_order(payload: OrderInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    plan = await db.get(SubscriptionPlan, payload.plan_id)
    if not plan or plan.status != "active": raise HTTPException(404, "Plan not found")
    amount = plan.price_paise
    coupon_code = payload.coupon_code.upper() if payload.coupon_code else None
    if coupon_code:
        coupon = await db.scalar(select(Coupon).where(Coupon.code == coupon_code, Coupon.status == "active"))
        if not coupon or (coupon.valid_until and coupon.valid_until <= datetime.now(UTC)) or (coupon.max_uses is not None and coupon.used_count >= coupon.max_uses): raise HTTPException(400, "Coupon is invalid or exhausted")
        amount = max(0, amount - (amount * coupon.discount_percent // 100))
    order = client().order.create({"amount": amount, "currency": "INR", "receipt": f"tnpsc-{uuid.uuid4().hex[:18]}", "notes": {"user_id": str(user.id), "plan_id": str(plan.id)}})
    payment = Payment(user_id=user.id, plan_id=plan.id, amount_paise=amount, razorpay_order_id=order["id"], coupon_code=coupon_code, created_by=user.id, updated_by=user.id); db.add(payment); await db.commit()
    return {"data": {"order_id": order["id"], "amount": amount, "currency": "INR", "key_id": get_settings().razorpay_key_id}}

async def activate_payment(db: AsyncSession, payment: Payment, payment_id: str) -> None:
    if payment.status == "paid": return
    plan = await db.get(SubscriptionPlan, payment.plan_id)
    payment.razorpay_payment_id, payment.status, payment.invoice_number = payment_id, "paid", f"INV-{datetime.now(UTC):%Y%m%d}-{payment.id.hex[:8].upper()}"
    if payment.coupon_code:
        coupon = await db.scalar(select(Coupon).where(Coupon.code == payment.coupon_code))
        if coupon: coupon.used_count += 1
    db.add(Subscription(user_id=payment.user_id, plan_id=plan.id, starts_at=datetime.now(UTC), ends_at=datetime.now(UTC) + timedelta(days=plan.duration_days), created_by=payment.user_id, updated_by=payment.user_id))
    await db.commit()

@router.post("/payments/verify")
async def verify_payment(payload: PaymentVerify, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    payment = await db.scalar(select(Payment).where(Payment.razorpay_order_id == payload.razorpay_order_id, Payment.user_id == user.id))
    if not payment: raise HTTPException(404, "Order not found")
    try: client().utility.verify_payment_signature(payload.model_dump())
    except Exception: raise HTTPException(400, "Invalid payment signature")
    await activate_payment(db, payment, payload.razorpay_payment_id); return {"message": "Payment verified", "invoice_number": payment.invoice_number}

@router.get("/payments/invoices/{invoice_number}")
async def invoice(invoice_number: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    payment = await db.scalar(select(Payment).where(Payment.invoice_number == invoice_number, Payment.user_id == user.id, Payment.status == "paid"))
    if not payment: raise HTTPException(404, "Invoice not found")
    plan = await db.get(SubscriptionPlan, payment.plan_id)
    return {"data": {"invoice_number": payment.invoice_number, "payment_id": payment.razorpay_payment_id, "amount_paise": payment.amount_paise, "currency": "INR", "plan": plan.name if plan else None, "issued_at": payment.updated_at}}

@router.post("/payments/webhook", include_in_schema=False)
async def webhook(request: Request, x_razorpay_signature: str = Header(default=""), db: AsyncSession = Depends(get_db)):
    secret = get_settings().razorpay_webhook_secret
    if not secret: raise HTTPException(503, "Webhook not configured")
    raw_body = await request.body()
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_razorpay_signature): raise HTTPException(400, "Invalid webhook signature")
    payload = json.loads(raw_body)
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {}); order_id = entity.get("order_id")
    if payload.get("event") == "payment.captured" and order_id:
        payment = await db.scalar(select(Payment).where(Payment.razorpay_order_id == order_id))
        if payment: await activate_payment(db, payment, entity["id"])
    return {"status": "ok"}

@router.post("/admin/notifications", dependencies=[Depends(require_permissions("notifications:write"))], status_code=201)
async def broadcast(payload: NotificationInput, bg: BackgroundTasks, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    notification = Notification(title=payload.title, body=payload.body, data_json=payload.data, created_by=user.id, updated_by=user.id); db.add(notification); await db.commit()
    bg.add_task(send_topic_notification, payload.title, payload.body, "manual", str(notification.id)); return {"data": {"id": str(notification.id)}}

@router.get("/current-affairs")
async def current_affairs(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(CurrentAffairs).where(CurrentAffairs.status == "active", CurrentAffairs.deleted_at.is_(None)).order_by(CurrentAffairs.published_at.desc()))).all()
    return {"data": [{"id": str(item.id), "title": item.title, "body": item.body, "published_at": item.published_at} for item in rows]}

@router.post("/admin/current-affairs", status_code=201, dependencies=[Depends(require_permissions("content:write"))])
async def create_current_affairs(payload: CurrentAffairsInput, bg: BackgroundTasks, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = CurrentAffairs(title=payload.title, body=payload.body, published_at=payload.published_at or datetime.now(UTC), created_by=user.id, updated_by=user.id); db.add(item); await db.commit()
    bg.add_task(send_topic_notification, "New current affairs", item.title, "current_affairs", str(item.id)); return {"data": {"id": str(item.id)}}

@router.post("/admin/coupons", status_code=201, dependencies=[Depends(require_permissions("subscriptions:write"))])
async def create_coupon(payload: CouponInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(Coupon.id).where(Coupon.code == payload.code.upper()))
    if exists: raise HTTPException(409, "Coupon code already exists")
    coupon = Coupon(**{**payload.model_dump(), "code": payload.code.upper()}, created_by=user.id, updated_by=user.id); db.add(coupon); await db.commit(); return {"data": {"id": str(coupon.id), "code": coupon.code}}

@router.get("/admin/users", dependencies=[Depends(require_permissions("admin:read"))])
async def admin_users(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc()).limit(200))).all()
    return {"data": [{"id": str(item.id), "phone": item.phone, "display_name": item.display_name, "status": item.status, "created_at": item.created_at} for item in rows]}

@router.get("/admin/settings/{key}", dependencies=[Depends(require_permissions("admin:read"))])
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Setting).where(Setting.key == key, Setting.deleted_at.is_(None)))
    if not item: raise HTTPException(404, "Setting not found")
    return {"data": {"key": item.key, "value": item.value_json}}

@router.put("/admin/settings/{key}", dependencies=[Depends(require_permissions("admin:write"))])
async def put_setting(key: str, payload: SettingInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Setting).where(Setting.key == key, Setting.deleted_at.is_(None)))
    if item: item.value_json, item.updated_by = payload.value, user.id
    else: db.add(Setting(key=key, value_json=payload.value, created_by=user.id, updated_by=user.id))
    await db.commit(); return {"message": "Setting saved"}

@router.get("/admin/dashboard", dependencies=[Depends(require_permissions("admin:read"))])
async def dashboard(db: AsyncSession = Depends(get_db)):
    users, revenue, attempts = await db.scalar(select(func.count(User.id))), await db.scalar(select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(Payment.status == "paid")), await db.scalar(select(func.count(TestAttempt.id)))
    return {"data": {"users": users, "revenue_paise": revenue, "attempts": attempts}}
