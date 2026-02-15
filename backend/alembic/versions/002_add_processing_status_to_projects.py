"""Add processing_status, processing_message, processing_started_at columns to projects table

Revision ID: 002
Revises: 001
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("processing_status", sa.String(50), nullable=True))
    op.add_column("projects", sa.Column("processing_message", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "processing_started_at")
    op.drop_column("projects", "processing_message")
    op.drop_column("projects", "processing_status")
