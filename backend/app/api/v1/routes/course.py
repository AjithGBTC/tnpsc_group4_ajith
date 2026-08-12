"""Dedicated mobile and admin APIs for the TNPSC course hierarchy."""
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies.auth import current_user, require_permissions
from app.models.course import (Chapter, CourseAnswer, CourseAttempt, CoursePdf, CourseQuestion, CourseTest, CourseVideo, QuestionOption, Subject, Unit)
from app.models.entities import User
from app.schemas.course import AnswerIn, ChapterIn, PdfIn, QuestionIn, SubmitIn, SubjectIn, TestIn, UnitIn, VideoIn
from app.services.storage import StorageService

router = APIRouter(tags=["TNPSC Course"])
ADMIN_MODELS = {"subjects": (Subject, SubjectIn), "units": (Unit, UnitIn), "chapters": (Chapter, ChapterIn), "videos": (CourseVideo, VideoIn), "pdfs": (CoursePdf, PdfIn), "tests": (CourseTest, TestIn)}

def out(item):
    return {column.name: (str(value) if isinstance(value, uuid.UUID) else value) for column in item.__table__.columns if (value := getattr(item, column.name)) is not None}

@router.get("/mobile/syllabus")
async def syllabus(db: AsyncSession = Depends(get_db)):
    subjects = (await db.scalars(select(Subject).where(Subject.deleted_at.is_(None), Subject.status == "active").order_by(Subject.category, Subject.title_english))).all()
    units = (await db.scalars(select(Unit).where(Unit.deleted_at.is_(None), Unit.status == "active").order_by(Unit.unit_number))).all()
    chapters = (await db.scalars(select(Chapter).where(Chapter.deleted_at.is_(None), Chapter.status == "active").order_by(Chapter.chapter_number))).all()
    return {"data": [{**out(s), "units": [{**out(u), "chapters": [out(c) for c in chapters if c.unit_id == u.id]} for u in units if u.subject_id == s.id]} for s in subjects]}

@router.get("/mobile/chapters/{chapter_id}/content")
async def chapter_content(chapter_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    if not await db.get(Chapter, chapter_id): raise HTTPException(404, "Chapter not found")
    async def rows(model): return (await db.scalars(select(model).where(model.chapter_id == chapter_id, model.deleted_at.is_(None), model.status == "active"))).all()
    return {"data": {"videos": [out(x) for x in await rows(CourseVideo)], "pdfs": [out(x) for x in await rows(CoursePdf)], "tests": [out(x) for x in await rows(CourseTest)]}}

@router.get("/mobile/course/tests")
async def tests(chapter_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    query = select(CourseTest).where(CourseTest.deleted_at.is_(None), CourseTest.status == "active")
    if chapter_id: query = query.where(CourseTest.chapter_id == chapter_id)
    return {"data": [out(x) for x in (await db.scalars(query.order_by(CourseTest.created_at.desc()))).all()]}

@router.post("/mobile/course/tests/{test_id}/start")
async def start_test(test_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    test = await db.get(CourseTest, test_id)
    if not test or test.deleted_at or test.status != "active": raise HTTPException(404, "Test not found")
    questions = (await db.scalars(select(CourseQuestion).where(CourseQuestion.test_id == test_id, CourseQuestion.deleted_at.is_(None)).order_by(CourseQuestion.created_at))).all()
    return {"data": {"test": out(test), "questions": [{**out(q), "options": [out(o) | {"is_correct": None} for o in (await db.scalars(select(QuestionOption).where(QuestionOption.question_id == q.id, QuestionOption.deleted_at.is_(None)))).all()]} for q in questions]}}

@router.post("/mobile/course/tests/{test_id}/submit")
async def submit_test(test_id: uuid.UUID, payload: SubmitIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    test = await db.get(CourseTest, test_id)
    if not test or test.deleted_at: raise HTTPException(404, "Test not found")
    questions = (await db.scalars(select(CourseQuestion).where(CourseQuestion.test_id == test_id, CourseQuestion.deleted_at.is_(None)))).all()
    question_map = {q.id: q for q in questions}; answer_map = {a.question_id: a.option_ids for a in payload.answers}
    if not set(answer_map).issubset(question_map): raise HTTPException(422, "Answer contains a question outside this test")
    score = 0; attempt = CourseAttempt(test_id=test_id, user_id=user.id, total_questions=len(questions), created_by=user.id, updated_by=user.id)
    db.add(attempt); await db.flush()
    for question_id, selected in answer_map.items():
        options = (await db.scalars(select(QuestionOption).where(QuestionOption.question_id == question_id, QuestionOption.deleted_at.is_(None)))).all()
        valid, correct = {o.id for o in options}, {o.id for o in options if o.is_correct}
        if not set(selected).issubset(valid): raise HTTPException(422, "Invalid option for question")
        if set(selected) == correct: score += 1
        db.add(CourseAnswer(attempt_id=attempt.id, question_id=question_id, option_ids=[str(x) for x in selected], created_by=user.id, updated_by=user.id))
    attempt.score = score; await db.commit()
    return {"data": {"attempt_id": str(attempt.id), "score": score, "total_questions": len(questions)}}

@router.get("/mobile/course/tests/{test_id}/leaderboard")
async def leaderboard(test_id: uuid.UUID, limit: int = 50, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CourseAttempt, User.display_name).join(User, User.id == CourseAttempt.user_id).where(CourseAttempt.test_id == test_id, CourseAttempt.deleted_at.is_(None)).order_by(CourseAttempt.score.desc(), CourseAttempt.created_at.asc()).limit(min(limit, 100)))).all()
    return {"data": [{"rank": i, "user_name": name, "score": attempt.score, "total_questions": attempt.total_questions} for i, (attempt, name) in enumerate(rows, 1)]}

@router.get("/admin/course/{resource}", dependencies=[Depends(require_permissions("content:write"))])
async def admin_list(resource: str, db: AsyncSession = Depends(get_db)):
    pair = ADMIN_MODELS.get(resource)
    if not pair: raise HTTPException(404, "Unknown resource")
    return {"data": [out(x) for x in (await db.scalars(select(pair[0]).where(pair[0].deleted_at.is_(None)))).all()]}

@router.post("/admin/course/{resource}", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("content:write"))])
async def admin_create(resource: str, payload: dict, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    pair = ADMIN_MODELS.get(resource)
    if not pair: raise HTTPException(404, "Unknown resource")
    values = pair[1].model_validate(payload).model_dump(); item = pair[0](**values, created_by=user.id, updated_by=user.id)
    db.add(item); await db.commit(); await db.refresh(item); return {"data": out(item)}

@router.patch("/admin/course/{resource}/{item_id}", dependencies=[Depends(require_permissions("content:write"))])
async def admin_update(resource: str, item_id: uuid.UUID, payload: dict, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    pair = ADMIN_MODELS.get(resource); item = await db.get(pair[0], item_id) if pair else None
    if not item or item.deleted_at: raise HTTPException(404, "Resource not found")
    values = pair[1].model_validate({**out(item), **payload}).model_dump()
    for key, value in values.items(): setattr(item, key, value)
    item.updated_by = user.id; await db.commit(); return {"data": out(item)}

@router.delete("/admin/course/{resource}/{item_id}", status_code=204, dependencies=[Depends(require_permissions("content:write"))])
async def admin_delete(resource: str, item_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    from datetime import UTC, datetime
    pair = ADMIN_MODELS.get(resource); item = await db.get(pair[0], item_id) if pair else None
    if not item or item.deleted_at: raise HTTPException(404, "Resource not found")
    item.deleted_at = datetime.now(UTC); item.updated_by = user.id; await db.commit()

@router.post("/admin/course/questions", status_code=201, dependencies=[Depends(require_permissions("questions:write"))])
async def create_question(payload: QuestionIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    values = payload.model_dump(exclude={"options"}); question = CourseQuestion(**values, created_by=user.id, updated_by=user.id); db.add(question); await db.flush()
    db.add_all([QuestionOption(question_id=question.id, **o.model_dump(), created_by=user.id, updated_by=user.id) for o in payload.options])
    test = await db.get(CourseTest, question.test_id); test.total_questions += 1
    await db.commit(); return {"data": {"id": str(question.id)}}

@router.post("/admin/uploads", dependencies=[Depends(require_permissions("content:write"))])
async def upload_file(file: UploadFile = File(...), user: User = Depends(current_user)):
    url = await StorageService().upload(file)
    return {"data": {"url": url, "content_type": file.content_type}}
