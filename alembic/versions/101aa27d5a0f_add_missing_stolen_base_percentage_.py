"""Add missing stolen_base_percentage column to catching_stats

Revision ID: 101aa27d5a0f
Revises: 3aaa2ce46b42
Create Date: 2025-07-21 18:31:58.016438

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "101aa27d5a0f"
down_revision = "3aaa2ce46b42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catching_stats",
        sa.Column("stolen_base_percentage", sa.Float(), default=0.0, nullable=True),
    )


def downgrade() -> None:
    # Remove the stolen_base_percentage column
    op.drop_column("catching_stats", "stolen_base_percentage")
