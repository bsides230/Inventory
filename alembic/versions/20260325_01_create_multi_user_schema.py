"""create multi user schema

Revision ID: 20260325_01
Revises: 
Create Date: 2026-03-25 21:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260325_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_external_id", "users", ["external_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "order_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("needed_by", sa.String(length=128), nullable=True),
        sa.Column("is_rush", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_order_drafts_user_id", "order_drafts", ["user_id"], unique=False)

    op.create_table(
        "order_draft_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("order_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("category_id", sa.String(length=128), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("draft_id", "item_id", name="uq_order_draft_item"),
    )
    op.create_index("ix_order_draft_items_draft_id", "order_draft_items", ["draft_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("is_rush", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("needed_by", sa.String(length=128), nullable=True),
        sa.Column("export_filename", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("category_id", sa.String(length=128), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"], unique=False)

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_order_draft_items_draft_id", table_name="order_draft_items")
    op.drop_table("order_draft_items")
    op.drop_index("ix_order_drafts_user_id", table_name="order_drafts")
    op.drop_table("order_drafts")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_table("users")
