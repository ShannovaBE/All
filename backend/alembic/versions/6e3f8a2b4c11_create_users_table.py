"""create users table

Revision ID: 6e3f8a2b4c11
Revises: 5d2b7c9a10ef
Create Date: 2026-06-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "6e3f8a2b4c11"
down_revision = "5d2b7c9a10ef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False, server_default="free"),
        sa.Column("kyb_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("restricted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_plan", "users", ["plan"])
    op.create_index("ix_users_kyb_status", "users", ["kyb_status"])
    op.create_index("ix_users_restricted", "users", ["restricted"])


def downgrade() -> None:
    op.drop_index("ix_users_restricted", table_name="users")
    op.drop_index("ix_users_kyb_status", table_name="users")
    op.drop_index("ix_users_plan", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
