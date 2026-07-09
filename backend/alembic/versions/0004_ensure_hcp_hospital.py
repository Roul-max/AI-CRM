"""Ensure hcps.hospital column exists (idempotent)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-10 00:00:00.000000

Migration 0003 added hcps.hospital but may not have been applied to all
environments. This migration is idempotent: it adds the column only when
it is absent, so it is safe to run regardless of whether 0003 ran.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    if not _column_exists("hcps", "hospital"):
        op.add_column("hcps", sa.Column("hospital", sa.String(), nullable=True))


def downgrade() -> None:
    if _column_exists("hcps", "hospital"):
        op.drop_column("hcps", "hospital")
