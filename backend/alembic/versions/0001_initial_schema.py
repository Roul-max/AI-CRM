"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-07-08 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'hcps',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=False, index=True),
        sa.Column('specialty', sa.String(), nullable=True),
    )

    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'competitors',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'interactions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('hcp_id', sa.Integer(), sa.ForeignKey('hcps.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('interaction_date', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('action_items', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.Column('risk_level', sa.String(), nullable=True),
    )

    op.create_table(
        'interaction_product',
        sa.Column('interaction_id', sa.Integer(), sa.ForeignKey('interactions.id'), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), primary_key=True),
    )

    op.create_table(
        'interaction_competitor',
        sa.Column('interaction_id', sa.Integer(), sa.ForeignKey('interactions.id'), primary_key=True),
        sa.Column('competitor_id', sa.Integer(), sa.ForeignKey('competitors.id'), primary_key=True),
    )

    op.create_table(
        'followups',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('interaction_id', sa.Integer(), sa.ForeignKey('interactions.id'), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('notes', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('followups')
    op.drop_table('interaction_competitor')
    op.drop_table('interaction_product')
    op.drop_table('interactions')
    op.drop_table('competitors')
    op.drop_table('products')
    op.drop_table('hcps')
    op.drop_table('users')
