from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies.auth import current_user, require_permissions
from app.models.entities import Question, Taxonomy
from app.schemas.content import QuestionCreate, TaxonomyCreate

router = APIRouter(tags=["Content"])

@router.get("/taxonomies/{kind}")
async def list_taxonomy(kind: str, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    query = select(Taxonomy).where(Taxonomy.kind == kind, Taxonomy.deleted_at.is_(None)).order_by(Taxonomy.sequence, Taxonomy.name).offset((page - 1) * size).limit(size)
    items = (await db.scalars(query)).all()
    return {"data": [{"id": str(x.id), "name": x.name, "parent_id": str(x.parent_id) if x.parent_id else None, "status": x.status} for x in items], "meta": {"page": page, "size": size}}

@router.post("/taxonomies/{kind}", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("content:write"))])
async def create_taxonomy(kind: str, payload: TaxonomyCreate, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    entity = Taxonomy(kind=kind, **payload.model_dump(), created_by=user.id, updated_by=user.id)
    db.add(entity); await db.commit(); await db.refresh(entity)
    return {"data": {"id": str(entity.id), "name": entity.name}}

@router.get("/questions")
async def list_questions(exam_id: str | None = None, approval_status: str | None = None, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    query = select(Question).where(Question.deleted_at.is_(None))
    if exam_id: query = query.where(Question.exam_id == exam_id)
    if approval_status: query = query.where(Question.approval_status == approval_status)
    items = (await db.scalars(query.order_by(Question.created_at.desc()).offset((page - 1) * size).limit(size))).all()
    return {"data": [{"id": str(q.id), "body": q.body, "status": q.approval_status, "difficulty": q.difficulty} for q in items], "meta": {"page": page, "size": size}}

@router.post("/questions", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("questions:write"))])
async def create_question(payload: QuestionCreate, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    question = Question(**payload.model_dump(), created_by=user.id, updated_by=user.id)
    db.add(question); await db.commit(); await db.refresh(question)
    return {"data": {"id": str(question.id), "approval_status": question.approval_status}}
