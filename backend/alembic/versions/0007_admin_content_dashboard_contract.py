"""Persist the Flutter admin course video/PDF contract.

Revision ID: 0007_admin_content_dashboard_contract
Revises: 0006_private_course_assets
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_admin_content_dashboard_contract"
down_revision = "0006_private_course_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("course_videos", sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("course_videos", sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_course_videos_subject_id_subjects", "course_videos", "subjects", ["subject_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_course_videos_unit_id_units", "course_videos", "units", ["unit_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_course_videos_subject_id", "course_videos", ["subject_id"])
    op.create_index("ix_course_videos_unit_id", "course_videos", ["unit_id"])
    op.add_column("course_videos", sa.Column("description", sa.Text(), nullable=True))
    op.alter_column("course_videos", "duration", type_=sa.String(length=80), postgresql_using="duration::text")
    op.add_column("course_videos", sa.Column("quiz_questions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))

    op.add_column("course_pdfs", sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("course_pdfs", sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_course_pdfs_subject_id_subjects", "course_pdfs", "subjects", ["subject_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_course_pdfs_unit_id_units", "course_pdfs", "units", ["unit_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_course_pdfs_subject_id", "course_pdfs", ["subject_id"])
    op.create_index("ix_course_pdfs_unit_id", "course_pdfs", ["unit_id"])
    op.add_column("course_pdfs", sa.Column("title_tamil", sa.String(length=240), nullable=True))
    op.add_column("course_pdfs", sa.Column("title_english", sa.String(length=240), nullable=True))
    op.add_column("course_pdfs", sa.Column("category", sa.String(length=120), nullable=True))
    op.add_column("course_pdfs", sa.Column("author", sa.String(length=160), nullable=True))
    op.add_column("course_pdfs", sa.Column("file_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    for table, prefix in (("course_pdfs", "course_pdfs"), ("course_videos", "course_videos")):
        op.drop_index(f"ix_{prefix}_unit_id", table_name=table)
        op.drop_index(f"ix_{prefix}_subject_id", table_name=table)
        op.drop_constraint(f"fk_{prefix}_unit_id_units", table, type_="foreignkey")
        op.drop_constraint(f"fk_{prefix}_subject_id_subjects", table, type_="foreignkey")
    for column in ("file_size", "author", "category", "title_english", "title_tamil", "unit_id", "subject_id"):
        op.drop_column("course_pdfs", column)
    op.drop_column("course_videos", "quiz_questions")
    op.alter_column("course_videos", "duration", type_=sa.Integer(), postgresql_using="NULLIF(duration, '')::integer")
    for column in ("description", "unit_id", "subject_id"):
        op.drop_column("course_videos", column)
