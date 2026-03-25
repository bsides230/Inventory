"""add order delivery fields

Revision ID: 20260325_02
Revises: 20260325_01
Create Date: 2026-03-25 22:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260325_02"
down_revision = "20260325_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("delivery_status", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("orders", sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("delivery_error", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivered_at")
    op.drop_column("orders", "delivery_error")
    op.drop_column("orders", "delivery_attempts")
    op.drop_column("orders", "delivery_status")
