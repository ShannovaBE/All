"""add dataset compliance fields

Revision ID: 4a6e8f0c2b19
Revises: 3f9a2c1b8d71
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "4a6e8f0c2b19"
down_revision: Union[str, None] = "3f9a2c1b8d71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    json_type = postgresql.JSONB(astext_type=sa.Text()) if dialect == "postgresql" else sa.JSON()
    empty_json = "'{}'::jsonb" if dialect == "postgresql" else "'{}'"
    op.add_column("dataset_records", sa.Column("provenance", json_type, nullable=True))
    op.add_column("dataset_records", sa.Column("compliance_evidence", json_type, nullable=True))
    op.add_column("dataset_records", sa.Column("access_policy", json_type, nullable=True))
    op.add_column("dataset_records", sa.Column("restriction_status", sa.Text(), nullable=True))
    op.execute(f"UPDATE dataset_records SET provenance = {empty_json} WHERE provenance IS NULL")
    op.execute(f"UPDATE dataset_records SET compliance_evidence = {empty_json} WHERE compliance_evidence IS NULL")
    op.execute(f"UPDATE dataset_records SET access_policy = {empty_json} WHERE access_policy IS NULL")
    op.execute("UPDATE dataset_records SET restriction_status = 'active' WHERE restriction_status IS NULL")
    if dialect != "sqlite":
        op.alter_column("dataset_records", "provenance", nullable=False)
        op.alter_column("dataset_records", "compliance_evidence", nullable=False)
        op.alter_column("dataset_records", "access_policy", nullable=False)
        op.alter_column("dataset_records", "restriction_status", nullable=False)
    op.create_index("ix_dataset_records_restriction_status", "dataset_records", ["restriction_status"])


def downgrade() -> None:
    op.drop_index("ix_dataset_records_restriction_status", table_name="dataset_records")
    op.drop_column("dataset_records", "restriction_status")
    op.drop_column("dataset_records", "access_policy")
    op.drop_column("dataset_records", "compliance_evidence")
    op.drop_column("dataset_records", "provenance")
