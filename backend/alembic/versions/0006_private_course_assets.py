"""Add HLS processing and PDF access metadata.

Revision ID: 0006_private_course_assets
Revises: 0005_course_question_chapter
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_private_course_assets"
down_revision = "0005_course_question_chapter"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("course_videos", sa.Column("hls_url", sa.String(length=1000), nullable=True))
    op.add_column("course_videos", sa.Column("transcoding_status", sa.String(length=32), nullable=False, server_default="pending"))
    op.create_index("ix_course_videos_transcoding_status", "course_videos", ["transcoding_status"])
    op.add_column("course_pdfs", sa.Column("offline_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("course_pdfs", sa.Column("is_priority", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("course_pdfs", "is_priority")
    op.drop_column("course_pdfs", "offline_allowed")
    op.drop_index("ix_course_videos_transcoding_status", table_name="course_videos")
    op.drop_column("course_videos", "transcoding_status")
    op.drop_column("course_videos", "hls_url")
