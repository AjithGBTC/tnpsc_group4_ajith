"""TNPSC Group 4 syllabus and assessment domain.

This module deliberately keeps the course hierarchy independent from the older
generic taxonomy feature, allowing a safe, incremental migration of content.
"""
import uuid
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import AuditModel


class Subject(AuditModel):
    __tablename__ = "subjects"
    title_tamil: Mapped[str] = mapped_column(String(240), nullable=False)
    title_english: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)


class Unit(AuditModel):
    __tablename__ = "units"
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_tamil: Mapped[str] = mapped_column(String(240), nullable=False)
    title_english: Mapped[str] = mapped_column(String(240), nullable=False)
    __table_args__ = (UniqueConstraint("subject_id", "unit_number"),)


class Chapter(AuditModel):
    __tablename__ = "chapters"
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_tamil: Mapped[str] = mapped_column(String(240), nullable=False)
    title_english: Mapped[str] = mapped_column(String(240), nullable=False)
    standard: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("unit_id", "chapter_number"),)


class CourseVideo(AuditModel):
    __tablename__ = "course_videos"
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    title_tamil: Mapped[str] = mapped_column(String(240), nullable=False)
    title_english: Mapped[str] = mapped_column(String(240), nullable=False)
    faculty_name: Mapped[str | None] = mapped_column(String(160))
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))
    duration: Mapped[int | None] = mapped_column(Integer)
    notes_url: Mapped[str | None] = mapped_column(String(1000))
    hls_url: Mapped[str | None] = mapped_column(String(1000))
    transcoding_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)


class CoursePdf(AuditModel):
    __tablename__ = "course_pdfs"
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    offline_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CourseTest(AuditModel):
    __tablename__ = "course_tests"
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CourseQuestion(AuditModel):
    __tablename__ = "course_questions"
    test_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), default="single_choice", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000))


class QuestionOption(AuditModel):
    __tablename__ = "question_options"
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CourseAttempt(AuditModel):
    __tablename__ = "course_attempts"
    test_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)


class CourseAnswer(AuditModel):
    __tablename__ = "course_answers"
    attempt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)
