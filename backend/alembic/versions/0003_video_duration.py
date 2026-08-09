"""Add video duration for admin media management."""
from alembic import op
import sqlalchemy as sa

revision = "0003_video_duration"
down_revision = "0002_learning_commerce"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("videos", sa.Column("duration_seconds", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("videos", "duration_seconds")
