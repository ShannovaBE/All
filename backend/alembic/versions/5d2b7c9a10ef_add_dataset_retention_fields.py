"""add dataset retention fields

Revision ID: 5d2b7c9a10ef
Revises: 4a6e8f0c2b19
Create Date: 2026-06-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "5d2b7c9a10ef"
down_revision = "4a6e8f0c2b19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dataset_records", sa.Column("retention_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("dataset_records", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE dataset_records SET retention_policy = '{}'::jsonb WHERE retention_policy IS NULL")
    op.alter_column("dataset_records", "retention_policy", nullable=False)
    op.create_index("ix_dataset_records_retention_expires_at", "dataset_records", ["retention_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_dataset_records_retention_expires_at", table_name="dataset_records")
    op.drop_column("dataset_records", "retention_expires_at")
    op.drop_column("dataset_records", "retention_policy")
