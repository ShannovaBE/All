"""create reviews table

Revision ID: 2b8d3c4e5f6a
Revises: 1c6f2d686103
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

revision = "2b8d3c4e5f6a"
down_revision = "1c6f2d686103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    timestamp_default = sa.text("now()") if op.get_bind().dialect.name == "postgresql" else sa.text("CURRENT_TIMESTAMP")
    op.create_table(
        "reviews",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="reviews_rating_range"),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="reviews_status_allowed",
        ),
    )
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"], unique=True)
    op.create_index("ix_reviews_status", "reviews", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reviews_status", table_name="reviews")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_table("reviews")
