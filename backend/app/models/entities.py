import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import AuditModel


class User(AuditModel):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Role(AuditModel):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)


class UserRole(AuditModel):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)


class RefreshSession(AuditModel):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    device_name: Mapped[str | None] = mapped_column(String(160))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Taxonomy(AuditModel):
    __tablename__ = "taxonomies"
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True) # exam, subject, chapter, topic
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("taxonomies.id"))
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    __table_args__ = (UniqueConstraint("kind", "name", "parent_id", name="uq_taxonomy_kind_name_parent"), Index("ix_taxonomy_kind_parent", "kind", "parent_id"))


class Question(AuditModel):
    __tablename__ = "questions"
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("taxonomies.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("taxonomies.id"), index=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("taxonomies.id"), index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    answer: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), default="single_choice", nullable=False)
    marks: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    negative_marks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)


class AuditLog(AuditModel):
    __tablename__ = "audit_logs"
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class PdfResource(AuditModel):
    __tablename__ = "pdf_resources"
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Test(AuditModel):
    __tablename__ = "tests"
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    test_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # practice, smart_quiz, live
    quiz_type: Mapped[str | None] = mapped_column(String(80), index=True)  # subject, topic, mixed, daily
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    resume_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TestQuestion(AuditModel):
    __tablename__ = "test_questions"
    test_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    __table_args__ = (UniqueConstraint("test_id", "question_id"),)


class TestAttempt(AuditModel):
    __tablename__ = "test_attempts"
    test_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="in_progress", nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_marks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    __table_args__ = (UniqueConstraint("test_id", "user_id", "attempt_number"),)


class AttemptAnswer(AuditModel):
    __tablename__ = "attempt_answers"
    attempt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    selected: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)
