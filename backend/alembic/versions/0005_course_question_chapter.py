"""Anchor course questions to their chapter.

Revision ID: 0005_course_question_chapter
Revises: 0004_tnpsc_course
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_course_question_chapter"
down_revision = "0004_tnpsc_course"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add as nullable, populate existing records from their test, then enforce
    # the application-level required field for all future Flutter uploads.
    op.add_column("course_questions", sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_course_questions_chapter_id_chapters",
        "course_questions", "chapters", ["chapter_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_course_questions_chapter_id", "course_questions", ["chapter_id"])
    op.execute("""
        UPDATE course_questions AS question
        SET chapter_id = test.chapter_id
        FROM course_tests AS test
        WHERE test.id = question.test_id AND test.chapter_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_course_questions_chapter_id", table_name="course_questions")
    op.drop_constraint("fk_course_questions_chapter_id_chapters", "course_questions", type_="foreignkey")
    op.drop_column("course_questions", "chapter_id")
