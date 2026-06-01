"""Create dataset_records table

Revision ID: 0001_create_dataset_records
Revises: None
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_create_dataset_records"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_records",
        sa.Column("file_hash", sa.Text(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("file_type", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("quality_scores", postgresql.JSONB(), nullable=False),
        sa.Column("category_verification", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("extra", postgresql.JSONB(), nullable=True),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("storage_provider", sa.Text(), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("bytes", sa.BigInteger(), nullable=True),
        sa.Column("mime", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("dataset_records")
