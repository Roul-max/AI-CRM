"""Ensure all interaction columns exist (idempotent)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-10 00:00:00.000000

Migration 0002 was stamped but never executed against this database, so the
following columns declared in the Interaction ORM model are absent:
  - interactions.outcomes
  - interactions.interaction_type
  - interactions.duration
  - interactions.brochure_shared
  - interactions.samples_requested

This migration adds each column only when it is absent, so it is safe to run
in any environment regardless of prior migration history.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    return any(
        c["name"] == column
        for c in inspect(op.get_bind()).get_columns(table)
    )


def upgrade() -> None:
    if not _column_exists("interactions", "outcomes"):
        op.add_column("interactions", sa.Column("outcomes", sa.Text(), nullable=True))

    if not _column_exists("interactions", "interaction_type"):
        op.add_column("interactions", sa.Column("interaction_type", sa.String(), nullable=True))

    if not _column_exists("interactions", "duration"):
        op.add_column("interactions", sa.Column("duration", sa.Integer(), nullable=True))

    if not _column_exists("interactions", "brochure_shared"):
        op.add_column("interactions", sa.Column("brochure_shared", sa.Boolean(), nullable=True))

    if not _column_exists("interactions", "samples_requested"):
        op.add_column("interactions", sa.Column("samples_requested", sa.Boolean(), nullable=True))


def downgrade() -> None:
    if _column_exists("interactions", "samples_requested"):
        op.drop_column("interactions", "samples_requested")

    if _column_exists("interactions", "brochure_shared"):
        op.drop_column("interactions", "brochure_shared")

    if _column_exists("interactions", "duration"):
        op.drop_column("interactions", "duration")

    if _column_exists("interactions", "interaction_type"):
        op.drop_column("interactions", "interaction_type")

    if _column_exists("interactions", "outcomes"):
        op.drop_column("interactions", "outcomes")
