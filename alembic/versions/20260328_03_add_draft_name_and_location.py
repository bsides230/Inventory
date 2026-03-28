"""add draft name and location tracking

Revision ID: 20260328_03
Revises: 20260325_02
Create Date: 2026-03-28 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260328_03"
down_revision = "20260325_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_drafts", sa.Column("draft_name", sa.String(length=128), nullable=True))
    op.add_column("orders", sa.Column("location_pin", sa.String(length=16), nullable=True))
    op.add_column("orders", sa.Column("location_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "location_name")
    op.drop_column("orders", "location_pin")
    op.drop_column("order_drafts", "draft_name")
