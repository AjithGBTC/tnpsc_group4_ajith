"""Add OTP, media, subscription, payment and notification domains."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_learning_commerce"
down_revision = "0001_mobile_learning"
branch_labels = None
depends_on = None

def audit():
    return [sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("deleted_at", sa.DateTime(timezone=True)), sa.Column("created_by", postgresql.UUID(as_uuid=True)), sa.Column("updated_by", postgresql.UUID(as_uuid=True)), sa.Column("status", sa.String(32), server_default="active", nullable=False), sa.Column("version", sa.Integer(), server_default="1", nullable=False)]

def upgrade():
    op.create_table("otp", *audit(), sa.Column("phone", sa.String(20), nullable=False), sa.Column("code_hash", sa.String(128), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("attempts", sa.Integer(), server_default="0", nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_otp_phone", "otp", ["phone"]); op.create_index("ix_otp_expires_at", "otp", ["expires_at"])
    op.add_column("pdf_resources", sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("taxonomies.id")))
    op.create_table("videos", *audit(), sa.Column("title", sa.String(240), nullable=False), sa.Column("description", sa.Text()), sa.Column("stream_url", sa.String(1000), nullable=False), sa.Column("thumbnail_url", sa.String(1000)), sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("taxonomies.id")), sa.Column("is_free", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table("subscription_plans", *audit(), sa.Column("name", sa.String(120), unique=True, nullable=False), sa.Column("price_paise", sa.Integer(), nullable=False), sa.Column("duration_days", sa.Integer(), nullable=False), sa.Column("test_limit", sa.Integer()), sa.Column("includes_video", sa.Boolean(), server_default=sa.false(), nullable=False), sa.Column("all_access", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table("coupons", *audit(), sa.Column("code", sa.String(64), unique=True, nullable=False), sa.Column("discount_percent", sa.Integer(), nullable=False), sa.Column("valid_until", sa.DateTime(timezone=True)), sa.Column("max_uses", sa.Integer()), sa.Column("used_count", sa.Integer(), server_default="0", nullable=False))
    op.create_table("subscriptions", *audit(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscription_plans.id"), nullable=False), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False), sa.Column("tests_used", sa.Integer(), server_default="0", nullable=False))
    op.create_table("payments", *audit(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False), sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscription_plans.id"), nullable=False), sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("razorpay_order_id", sa.String(128), unique=True, nullable=False), sa.Column("razorpay_payment_id", sa.String(128), unique=True), sa.Column("invoice_number", sa.String(64), unique=True), sa.Column("coupon_code", sa.String(64)))
    op.create_table("notifications", *audit(), sa.Column("title", sa.String(240), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("data_json", postgresql.JSONB(), nullable=False))
    op.create_table("device_tokens", *audit(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("token", sa.String(512), unique=True, nullable=False), sa.Column("platform", sa.String(20), nullable=False))
    op.create_table("current_affairs", *audit(), sa.Column("title", sa.String(240), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("settings", *audit(), sa.Column("key", sa.String(120), unique=True, nullable=False), sa.Column("value_json", postgresql.JSONB(), nullable=False))

def downgrade():
    for name in ("settings", "current_affairs", "device_tokens", "notifications", "payments", "subscriptions", "coupons", "subscription_plans", "videos"):
        op.drop_table(name)
    op.drop_column("pdf_resources", "topic_id")
    op.drop_index("ix_otp_expires_at", table_name="otp"); op.drop_index("ix_otp_phone", table_name="otp"); op.drop_table("otp")
