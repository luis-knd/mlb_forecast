"""Update catching stats table with all MLB API fields

Revision ID: 3aaa2ce46b42
Revises: dab74dcaefb6
Create Date: 2025-07-21 18:29:53.951584

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3aaa2ce46b42"
down_revision = "dab74dcaefb6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the non-existent innings_played field if it exists
    try:
        op.drop_column("catching_stats", "innings_played")
    except Exception:
        # Column might not exist, ignore the error
        pass

    # Add all the missing offensive stats fields
    op.add_column(
        "catching_stats",
        sa.Column("games_pitched", sa.Integer(), default=0, nullable=True),
    )
    op.add_column("catching_stats", sa.Column("at_bats", sa.Integer(), default=0, nullable=True))
    op.add_column("catching_stats", sa.Column("hits", sa.Integer(), default=0, nullable=True))
    op.add_column("catching_stats", sa.Column("runs", sa.Integer(), default=0, nullable=True))
    op.add_column("catching_stats", sa.Column("home_runs", sa.Integer(), default=0, nullable=True))
    op.add_column(
        "catching_stats",
        sa.Column("strikeouts", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("base_on_balls", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("intentional_walks", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("hit_by_pitch", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("total_bases", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("sacrifice_bunts", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("sacrifice_flies", sa.Integer(), default=0, nullable=True),
    )

    # Add batting averages and percentages
    op.add_column(
        "catching_stats",
        sa.Column("batting_average", sa.Float(), default=0.0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("on_base_percentage", sa.Float(), default=0.0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("slugging_percentage", sa.Float(), default=0.0, nullable=True),
    )
    op.add_column("catching_stats", sa.Column("ops", sa.Float(), default=0.0, nullable=True))

    # Add missing defensive stats
    op.add_column(
        "catching_stats",
        sa.Column("pickoff_attempts", sa.Integer(), default=0, nullable=True),
    )

    # Add pitching stats
    op.add_column(
        "catching_stats",
        sa.Column("earned_runs", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("batters_faced", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("hit_batsmen", sa.Integer(), default=0, nullable=True),
    )
    op.add_column(
        "catching_stats",
        sa.Column("strikeout_walk_ratio", sa.Float(), default=0.0, nullable=True),
    )


def downgrade() -> None:
    # Remove all the added columns
    op.drop_column("catching_stats", "strikeout_walk_ratio")
    op.drop_column("catching_stats", "hit_batsmen")
    op.drop_column("catching_stats", "batters_faced")
    op.drop_column("catching_stats", "earned_runs")
    op.drop_column("catching_stats", "pickoff_attempts")
    op.drop_column("catching_stats", "ops")
    op.drop_column("catching_stats", "slugging_percentage")
    op.drop_column("catching_stats", "on_base_percentage")
    op.drop_column("catching_stats", "batting_average")
    op.drop_column("catching_stats", "sacrifice_flies")
    op.drop_column("catching_stats", "sacrifice_bunts")
    op.drop_column("catching_stats", "total_bases")
    op.drop_column("catching_stats", "hit_by_pitch")
    op.drop_column("catching_stats", "intentional_walks")
    op.drop_column("catching_stats", "base_on_balls")
    op.drop_column("catching_stats", "strikeouts")
    op.drop_column("catching_stats", "home_runs")
    op.drop_column("catching_stats", "runs")
    op.drop_column("catching_stats", "hits")
    op.drop_column("catching_stats", "at_bats")
    op.drop_column("catching_stats", "games_pitched")

    # Re-add innings_played if needed for rollback
    op.add_column(
        "catching_stats",
        sa.Column("innings_played", sa.Float(), default=0.0, nullable=True),
    )
