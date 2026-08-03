import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import current_user, require_permissions
from app.models.entities import AttemptAnswer, PdfResource, Question, Test, TestAttempt, TestQuestion, User
from app.schemas.mobile import SaveAnswer, TestCreate
from app.services.notifications import send_topic_notification

router = APIRouter(tags=["Mobile learning"])
UPLOAD_DIR = Path("uploads/pdfs")


def now() -> datetime:
    return datetime.now(UTC)


async def get_attempt_or_404(db: AsyncSession, attempt_id: uuid.UUID, user_id: uuid.UUID) -> TestAttempt:
    attempt = await db.scalar(select(TestAttempt).where(TestAttempt.id == attempt_id, TestAttempt.user_id == user_id, TestAttempt.deleted_at.is_(None)))
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


async def finalize(db: AsyncSession, attempt: TestAttempt) -> None:
    if attempt.status != "in_progress":
        return
    questions = (await db.scalars(select(Question).join(TestQuestion, TestQuestion.question_id == Question.id).where(TestQuestion.test_id == attempt.test_id))).all()
    answers = (await db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id))).all()
    selected = {answer.question_id: answer.selected for answer in answers}
    score = 0
    total = 0
    for question in questions:
        total += question.marks
        if set(selected.get(question.id, [])) == set(question.answer):
            score += question.marks
        elif selected.get(question.id):
            score -= question.negative_marks
    attempt.score = max(0, score)
    attempt.total_marks = total
    attempt.status = "submitted"
    attempt.submitted_at = now()
    await db.commit()


def question_payload(question: Question) -> dict:
    return {"id": str(question.id), "body": question.body, "options": question.options, "difficulty": question.difficulty, "question_type": question.question_type, "marks": question.marks, "negative_marks": question.negative_marks}


@router.get("/mobile/pdfs")
async def list_pdfs(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(PdfResource).where(PdfResource.deleted_at.is_(None), PdfResource.status == "active").order_by(PdfResource.created_at.desc()))).all()
    return {"data": [{"id": str(pdf.id), "title": pdf.title, "description": pdf.description, "url": pdf.file_path, "is_free": pdf.is_free} for pdf in rows]}


@router.post("/admin/pdfs", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("content:write"))])
async def upload_pdf(background_tasks: BackgroundTasks, title: str, file: UploadFile = File(...), description: str | None = None, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are allowed")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.pdf"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    resource = PdfResource(title=title, description=description, file_path=f"/uploads/pdfs/{filename}", created_by=user.id, updated_by=user.id)
    db.add(resource)
    await db.commit()
    background_tasks.add_task(send_topic_notification, "New free PDF available", title, "pdf", str(resource.id))
    return {"data": {"id": str(resource.id), "url": resource.file_path}}


@router.get("/mobile/tests")
async def list_tests(test_type: str | None = Query(default=None), quiz_type: str | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    query = select(Test).where(Test.deleted_at.is_(None), Test.status == "active")
    if test_type:
        query = query.where(Test.test_type == test_type)
    if quiz_type:
        query = query.where(Test.quiz_type == quiz_type)
    rows = (await db.scalars(query.order_by(Test.starts_at.desc().nullslast(), Test.created_at.desc()))).all()
    return {"data": [{"id": str(test.id), "title": test.title, "description": test.description, "test_type": test.test_type, "quiz_type": test.quiz_type, "duration_minutes": test.duration_minutes, "max_attempts": test.max_attempts, "resume_allowed": test.resume_allowed, "starts_at": test.starts_at, "ends_at": test.ends_at} for test in rows]}


@router.post("/admin/tests", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions("content:write"))])
async def create_test(payload: TestCreate, background_tasks: BackgroundTasks, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if payload.test_type == "live" and (not payload.starts_at or not payload.ends_at):
        raise HTTPException(status_code=422, detail="Live tests require starts_at and ends_at")
    test_data = payload.model_dump(exclude={"question_ids"})
    if payload.test_type == "live":
        test_data["max_attempts"] = 1
    test = Test(**test_data, resume_allowed=payload.test_type != "live", created_by=user.id, updated_by=user.id)
    db.add(test)
    await db.flush()
    db.add_all([TestQuestion(test_id=test.id, question_id=question_id, sequence=index, created_by=user.id, updated_by=user.id) for index, question_id in enumerate(payload.question_ids, start=1)])
    await db.commit()
    if test.test_type == "live":
        background_tasks.add_task(send_topic_notification, "Live test announced", f"{test.title} is now available. Join on time!", "live_test", str(test.id))
    else:
        background_tasks.add_task(send_topic_notification, "New test available", test.title, "test", str(test.id))
    return {"data": {"id": str(test.id)}}


@router.post("/mobile/tests/{test_id}/start")
async def start_test(test_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    test = await db.get(Test, test_id)
    if not test or test.deleted_at or test.status != "active":
        raise HTTPException(status_code=404, detail="Test not found")
    current = now()
    if test.test_type == "live" and (not test.starts_at or not test.ends_at or current < test.starts_at or current >= test.ends_at):
        raise HTTPException(status_code=409, detail="Live test is not currently open")
    existing = await db.scalar(select(TestAttempt).where(TestAttempt.test_id == test_id, TestAttempt.user_id == user.id, TestAttempt.status == "in_progress").order_by(TestAttempt.started_at.desc()))
    if existing:
        if existing.expires_at <= current:
            await finalize(db, existing)
        elif test.resume_allowed:
            return {"data": {"attempt_id": str(existing.id), "status": "in_progress", "resumed": True, "expires_at": existing.expires_at}}
        else:
            raise HTTPException(status_code=409, detail="A live test cannot be resumed")
    completed = await db.scalar(select(func.count()).select_from(TestAttempt).where(TestAttempt.test_id == test_id, TestAttempt.user_id == user.id, TestAttempt.status == "submitted"))
    if completed >= test.max_attempts:
        raise HTTPException(status_code=409, detail="Maximum attempts reached")
    expires_at = current + timedelta(minutes=test.duration_minutes)
    if test.ends_at:
        expires_at = min(expires_at, test.ends_at)
    attempt = TestAttempt(test_id=test.id, user_id=user.id, attempt_number=completed + 1, started_at=current, expires_at=expires_at, created_by=user.id, updated_by=user.id)
    db.add(attempt)
    await db.commit()
    return {"data": {"attempt_id": str(attempt.id), "status": "in_progress", "resumed": False, "expires_at": expires_at}}


@router.get("/mobile/attempts/{attempt_id}")
async def get_attempt(attempt_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    attempt = await get_attempt_or_404(db, attempt_id, user.id)
    if attempt.status == "in_progress" and attempt.expires_at <= now():
        await finalize(db, attempt)
    questions = (await db.scalars(select(Question).join(TestQuestion, TestQuestion.question_id == Question.id).where(TestQuestion.test_id == attempt.test_id).order_by(TestQuestion.sequence))).all()
    return {"data": {"id": str(attempt.id), "status": attempt.status, "expires_at": attempt.expires_at, "remaining_seconds": max(0, int((attempt.expires_at - now()).total_seconds())), "questions": [question_payload(question) for question in questions]}}


@router.put("/mobile/attempts/{attempt_id}/answers")
async def save_answer(attempt_id: uuid.UUID, payload: SaveAnswer, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    attempt = await get_attempt_or_404(db, attempt_id, user.id)
    if attempt.status != "in_progress" or attempt.expires_at <= now():
        if attempt.status == "in_progress": await finalize(db, attempt)
        raise HTTPException(status_code=409, detail="Attempt is already closed")
    valid = await db.scalar(select(TestQuestion.id).where(TestQuestion.test_id == attempt.test_id, TestQuestion.question_id == payload.question_id))
    if not valid:
        raise HTTPException(status_code=400, detail="Question is not part of this test")
    answer = await db.scalar(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id, AttemptAnswer.question_id == payload.question_id))
    if answer: answer.selected = payload.selected
    else: db.add(AttemptAnswer(attempt_id=attempt.id, question_id=payload.question_id, selected=payload.selected, created_by=user.id, updated_by=user.id))
    await db.commit()
    return {"message": "Answer saved"}


@router.post("/mobile/attempts/{attempt_id}/submit")
async def submit_attempt(attempt_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    attempt = await get_attempt_or_404(db, attempt_id, user.id)
    await finalize(db, attempt)
    return {"data": {"attempt_id": str(attempt.id), "status": attempt.status, "score": attempt.score, "total_marks": attempt.total_marks}}


@router.get("/mobile/attempts/{attempt_id}/analysis")
async def attempt_analysis(attempt_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    attempt = await get_attempt_or_404(db, attempt_id, user.id)
    if attempt.status != "submitted": raise HTTPException(status_code=409, detail="Submit the test before viewing analysis")
    questions = (await db.scalars(select(Question).join(TestQuestion, TestQuestion.question_id == Question.id).where(TestQuestion.test_id == attempt.test_id))).all()
    answers = {row.question_id: row.selected for row in (await db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id))).all()}
    groups: dict[str, list[int]] = {}
    for question in questions:
        key = str(question.subject_id or "General")
        value = groups.setdefault(key, [0, 0])
        value[1] += 1
        value[0] += int(set(answers.get(question.id, [])) == set(question.answer))
    sections = [{"section": key, "correct": value[0], "total": value[1], "percentage": round(value[0] * 100 / value[1], 1)} for key, value in groups.items()]
    return {"data": {"score": attempt.score, "total_marks": attempt.total_marks, "percentage": round(attempt.score * 100 / attempt.total_marks, 1) if attempt.total_marks else 0, "strong": [item for item in sections if item["percentage"] >= 75], "improve": [item for item in sections if item["percentage"] < 75], "weaknesses": [item for item in sections if item["percentage"] < 50]}}


@router.get("/mobile/attempts/{attempt_id}/review")
async def review_attempt(attempt_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    attempt = await get_attempt_or_404(db, attempt_id, user.id)
    if attempt.status != "submitted": raise HTTPException(status_code=409, detail="Submit the test before reviewing it")
    questions = (await db.scalars(select(Question).join(TestQuestion, TestQuestion.question_id == Question.id).where(TestQuestion.test_id == attempt.test_id).order_by(TestQuestion.sequence))).all()
    answers = {row.question_id: row.selected for row in (await db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id))).all()}
    return {"data": [{**question_payload(question), "selected": answers.get(question.id, []), "correct_answer": question.answer, "is_correct": set(answers.get(question.id, [])) == set(question.answer), "explanation": question.explanation} for question in questions]}


@router.get("/mobile/attempts/{attempt_id}/live-rank")
async def live_rank(attempt_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    attempt = await get_attempt_or_404(db, attempt_id, user.id)
    test = await db.get(Test, attempt.test_id)
    if not test or test.test_type != "live" or attempt.status != "submitted": raise HTTPException(status_code=409, detail="Live-test result is not available")
    rows = (await db.scalars(select(TestAttempt).where(TestAttempt.test_id == test.id, TestAttempt.status == "submitted").order_by(TestAttempt.score.desc(), TestAttempt.submitted_at.asc()))).all()
    rank = next(index for index, row in enumerate(rows, start=1) if row.id == attempt.id)
    return {"data": {"rank": rank, "participants": len(rows), "score": attempt.score, "total_marks": attempt.total_marks}}
