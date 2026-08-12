"""Add the dedicated TNPSC syllabus, content and test domain."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_tnpsc_course"
down_revision = "0003_video_duration"
branch_labels = None
depends_on = None

audit = [
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("deleted_at", sa.DateTime(timezone=True)), sa.Column("created_by", postgresql.UUID(as_uuid=True)), sa.Column("updated_by", postgresql.UUID(as_uuid=True)),
    sa.Column("status", sa.String(32), nullable=False, server_default="active"), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
]
def table(name, *columns): op.create_table(name, *audit, *columns)
def upgrade():
    table("subjects", sa.Column("title_tamil", sa.String(240), nullable=False), sa.Column("title_english", sa.String(240), nullable=False), sa.Column("category", sa.String(20), nullable=False))
    table("units", sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False), sa.Column("unit_number", sa.Integer(), nullable=False), sa.Column("title_tamil", sa.String(240), nullable=False), sa.Column("title_english", sa.String(240), nullable=False), sa.UniqueConstraint("subject_id", "unit_number"))
    table("chapters", sa.Column("unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False), sa.Column("chapter_number", sa.Integer(), nullable=False), sa.Column("title_tamil", sa.String(240), nullable=False), sa.Column("title_english", sa.String(240), nullable=False), sa.Column("standard", sa.Integer(), nullable=False), sa.UniqueConstraint("unit_id", "chapter_number"))
    table("course_videos", sa.Column("chapter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False), sa.Column("title_tamil", sa.String(240), nullable=False), sa.Column("title_english", sa.String(240), nullable=False), sa.Column("faculty_name", sa.String(160)), sa.Column("video_url", sa.String(1000), nullable=False), sa.Column("thumbnail_url", sa.String(1000)), sa.Column("duration", sa.Integer()), sa.Column("notes_url", sa.String(1000)))
    table("course_pdfs", sa.Column("chapter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(240), nullable=False), sa.Column("description", sa.Text()), sa.Column("file_url", sa.String(1000), nullable=False))
    table("course_tests", sa.Column("chapter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="SET NULL")), sa.Column("title", sa.String(240), nullable=False), sa.Column("type", sa.String(20), nullable=False), sa.Column("duration", sa.Integer(), nullable=False), sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"))
    table("course_questions", sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("course_tests.id", ondelete="CASCADE"), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("explanation", sa.Text()), sa.Column("type", sa.String(20), nullable=False, server_default="single_choice"), sa.Column("image_url", sa.String(1000)))
    table("question_options", sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("course_questions.id", ondelete="CASCADE"), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()))
    table("course_attempts", sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("course_tests.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("score", sa.Integer(), nullable=False, server_default="0"), sa.Column("total_questions", sa.Integer(), nullable=False))
    table("course_answers", sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("course_attempts.id", ondelete="CASCADE"), nullable=False), sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("course_questions.id", ondelete="CASCADE"), nullable=False), sa.Column("option_ids", postgresql.JSONB(), nullable=False, server_default="[]"), sa.UniqueConstraint("attempt_id", "question_id"))
    for name in ("subjects", "units", "chapters", "course_videos", "course_pdfs", "course_tests", "course_questions", "question_options", "course_attempts", "course_answers"): op.create_index(f"ix_{name}_active", name, ["deleted_at", "status"])
def downgrade():
    for name in ("course_answers", "course_attempts", "question_options", "course_questions", "course_tests", "course_pdfs", "course_videos", "chapters", "units", "subjects"): op.drop_table(name)
