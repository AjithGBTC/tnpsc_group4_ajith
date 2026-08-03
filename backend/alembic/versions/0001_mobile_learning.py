"""Initial exam platform and TNPSC mobile learning tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_mobile_learning"
down_revision = None
branch_labels = None
depends_on = None


def audit_columns():
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    ]


def upgrade() -> None:
    op.create_table("users", *audit_columns(), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("phone", sa.String(20), unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("display_name", sa.String(160), nullable=False), sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table("roles", *audit_columns(), sa.Column("name", sa.String(80), nullable=False, unique=True), sa.Column("permissions", postgresql.JSONB(), nullable=False))
    op.create_table("user_roles", *audit_columns(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False), sa.UniqueConstraint("user_id", "role_id"))
    op.create_table("refresh_sessions", *audit_columns(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(128), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("device_name", sa.String(160)), sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_table("taxonomies", *audit_columns(), sa.Column("kind", sa.String(32), nullable=False), sa.Column("name", sa.String(240), nullable=False), sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("taxonomies.id")), sa.Column("sequence", sa.Integer(), server_default="0", nullable=False), sa.UniqueConstraint("kind", "name", "parent_id", name="uq_taxonomy_kind_name_parent"))
    op.create_table("questions", *audit_columns(), sa.Column("exam_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("taxonomies.id"), nullable=False), sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("taxonomies.id")), sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("taxonomies.id")), sa.Column("body", sa.Text(), nullable=False), sa.Column("options", postgresql.JSONB(), nullable=False), sa.Column("answer", postgresql.JSONB(), nullable=False), sa.Column("explanation", sa.Text()), sa.Column("difficulty", sa.String(32), server_default="medium", nullable=False), sa.Column("question_type", sa.String(32), server_default="single_choice", nullable=False), sa.Column("marks", sa.Integer(), server_default="1", nullable=False), sa.Column("negative_marks", sa.Integer(), server_default="0", nullable=False), sa.Column("approval_status", sa.String(32), server_default="draft", nullable=False))
    op.create_table("pdf_resources", *audit_columns(), sa.Column("title", sa.String(240), nullable=False), sa.Column("description", sa.Text()), sa.Column("file_path", sa.String(500), nullable=False), sa.Column("is_free", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_table("audit_logs", *audit_columns(), sa.Column("actor_id", postgresql.UUID(as_uuid=True)), sa.Column("action", sa.String(80), nullable=False), sa.Column("resource", sa.String(100), nullable=False), sa.Column("resource_id", sa.String(64)), sa.Column("metadata_json", postgresql.JSONB(), nullable=False))
    op.create_table("tests", *audit_columns(), sa.Column("title", sa.String(240), nullable=False), sa.Column("description", sa.Text()), sa.Column("test_type", sa.String(32), nullable=False), sa.Column("quiz_type", sa.String(80)), sa.Column("duration_minutes", sa.Integer(), nullable=False), sa.Column("max_attempts", sa.Integer(), server_default="2", nullable=False), sa.Column("resume_allowed", sa.Boolean(), server_default=sa.true(), nullable=False), sa.Column("starts_at", sa.DateTime(timezone=True)), sa.Column("ends_at", sa.DateTime(timezone=True)))
    op.create_table("test_questions", *audit_columns(), sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tests.id", ondelete="CASCADE"), nullable=False), sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False), sa.Column("sequence", sa.Integer(), server_default="0", nullable=False), sa.UniqueConstraint("test_id", "question_id"))
    op.create_table("test_attempts", *audit_columns(), sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tests.id"), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False), sa.Column("attempt_number", sa.Integer(), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("score", sa.Integer(), server_default="0", nullable=False), sa.Column("total_marks", sa.Integer(), server_default="0", nullable=False), sa.UniqueConstraint("test_id", "user_id", "attempt_number"))
    op.create_table("attempt_answers", *audit_columns(), sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False), sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id"), nullable=False), sa.Column("selected", postgresql.JSONB(), nullable=False), sa.UniqueConstraint("attempt_id", "question_id"))


def downgrade() -> None:
    for table in ("attempt_answers", "test_attempts", "test_questions", "tests", "audit_logs", "pdf_resources", "questions", "taxonomies", "refresh_sessions", "user_roles", "roles", "users"):
        op.drop_table(table)
