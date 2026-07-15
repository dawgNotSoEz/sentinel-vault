"""add_account_lockout

Revision ID: d0f80fb1be0c
Revises: 0001_initial_schema
Create Date: 2026-07-16 02:44:44.294454
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd0f80fb1be0c'
down_revision: str | None = '0001_initial_schema'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
