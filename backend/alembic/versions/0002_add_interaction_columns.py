"""Add missing interaction columns and make user_id nullable

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-09 00:00:00.000000

Adds columns that were present in the ORM model but missing from the
initial migration:
  - interactions.outcomes
  - interactions.interaction_type
  - interactions.duration
  - interactions.brochure_shared
  - interactions.samples_requested
  - interactions.user_id  -> alter to nullable (no auth yet)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make user_id nullable so saves work without a seeded user row
    op.alter_column('interactions', 'user_id', nullable=True)

    # Add new scalar columns — all nullable so existing rows are unaffected
    op.add_column('interactions', sa.Column('outcomes', sa.Text(), nullable=True))
    op.add_column('interactions', sa.Column('interaction_type', sa.String(), nullable=True))
    op.add_column('interactions', sa.Column('duration', sa.Integer(), nullable=True))
    op.add_column('interactions', sa.Column('brochure_shared', sa.Boolean(), nullable=True))
    op.add_column('interactions', sa.Column('samples_requested', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('interactions', 'samples_requested')
    op.drop_column('interactions', 'brochure_shared')
    op.drop_column('interactions', 'duration')
    op.drop_column('interactions', 'interaction_type')
    op.drop_column('interactions', 'outcomes')
    op.alter_column('interactions', 'user_id', nullable=False)
