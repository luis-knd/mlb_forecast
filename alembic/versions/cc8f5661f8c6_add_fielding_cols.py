"""Add fielding cols

Revision ID: cc8f5661f8c6
Revises: 5a21b4cfd6eb
Create Date: 2025-07-24 18:09:04.915282

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cc8f5661f8c6"
down_revision = "5a21b4cfd6eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing fielding stats columns to the fielding_stats table."""
    # Add games_started column after games_played
    op.add_column(
        "fielding_stats",
        sa.Column("games_started", sa.Integer(), default=0, nullable=True),
    )

    # Add throwing_errors column after errors
    op.add_column(
        "fielding_stats",
        sa.Column("throwing_errors", sa.Integer(), default=0, nullable=True),
    )

    # Add stolen_base_percentage column after caught_stealing
    op.add_column(
        "fielding_stats",
        sa.Column("stolen_base_percentage", sa.Float(), default=0.0, nullable=True),
    )

    # Add catchers_interference column after stolen_base_percentage
    op.add_column(
        "fielding_stats",
        sa.Column("catchers_interference", sa.Integer(), default=0, nullable=True),
    )

    # Set default values for existing rows
    op.execute("UPDATE fielding_stats SET games_started = 0 WHERE games_started IS NULL")
    op.execute("UPDATE fielding_stats SET throwing_errors = 0 WHERE throwing_errors IS NULL")
    op.execute("UPDATE fielding_stats SET stolen_base_percentage = 0.0 WHERE stolen_base_percentage IS NULL")
    op.execute("UPDATE fielding_stats SET catchers_interference = 0 WHERE catchers_interference IS NULL")

    # Make columns non-nullable after setting defaults
    op.alter_column("fielding_stats", "games_started", nullable=False)
    op.alter_column("fielding_stats", "throwing_errors", nullable=False)
    op.alter_column("fielding_stats", "stolen_base_percentage", nullable=False)
    op.alter_column("fielding_stats", "catchers_interference", nullable=False)


def downgrade() -> None:
    """Remove the added fielding stats columns."""
    op.drop_column("fielding_stats", "catchers_interference")
    op.drop_column("fielding_stats", "stolen_base_percentage")
    op.drop_column("fielding_stats", "throwing_errors")
    op.drop_column("fielding_stats", "games_started")
