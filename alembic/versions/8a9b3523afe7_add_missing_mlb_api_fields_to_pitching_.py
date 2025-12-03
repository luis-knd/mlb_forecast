"""Add missing MLB API fields to pitching_stats table

Revision ID: 8a9b3523afe7
Revises: e2fac52e98be
Create Date: 2025-07-24 17:25:56.031911

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8a9b3523afe7"
down_revision = "e2fac52e98be"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing basic stats columns from MLB API
    op.add_column("pitching_stats", sa.Column("doubles", sa.Integer(), nullable=True, default=0))
    op.add_column("pitching_stats", sa.Column("triples", sa.Integer(), nullable=True, default=0))
    op.add_column("pitching_stats", sa.Column("at_bats", sa.Integer(), nullable=True, default=0))
    op.add_column("pitching_stats", sa.Column("outs", sa.Integer(), nullable=True, default=0))
    op.add_column("pitching_stats", sa.Column("strikes", sa.Integer(), nullable=True, default=0))
    op.add_column("pitching_stats", sa.Column("pickoffs", sa.Integer(), nullable=True, default=0))
    op.add_column(
        "pitching_stats",
        sa.Column("total_bases", sa.Integer(), nullable=True, default=0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("games_finished", sa.Integer(), nullable=True, default=0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("catchers_interference", sa.Integer(), nullable=True, default=0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("sacrifice_bunts", sa.Integer(), nullable=True, default=0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("sacrifice_flies", sa.Integer(), nullable=True, default=0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("ground_into_double_play", sa.Integer(), nullable=True, default=0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("caught_stealing", sa.Integer(), nullable=True, default=0),
    )

    # Add missing advanced stats columns from MLB API
    op.add_column(
        "pitching_stats",
        sa.Column("on_base_percentage", sa.Float(), nullable=True, default=0.0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("slugging_percentage", sa.Float(), nullable=True, default=0.0),
    )
    op.add_column("pitching_stats", sa.Column("ops", sa.Float(), nullable=True, default=0.0))
    op.add_column(
        "pitching_stats",
        sa.Column("stolen_base_percentage", sa.Float(), nullable=True, default=0.0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("strike_percentage", sa.Float(), nullable=True, default=0.0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("win_percentage", sa.Float(), nullable=True, default=0.0),
    )
    op.add_column(
        "pitching_stats",
        sa.Column("runs_scored_per_nine", sa.Float(), nullable=True, default=0.0),
    )


def downgrade() -> None:
    # Remove all added columns in reverse order
    op.drop_column("pitching_stats", "runs_scored_per_nine")
    op.drop_column("pitching_stats", "win_percentage")
    op.drop_column("pitching_stats", "strike_percentage")
    op.drop_column("pitching_stats", "stolen_base_percentage")
    op.drop_column("pitching_stats", "ops")
    op.drop_column("pitching_stats", "slugging_percentage")
    op.drop_column("pitching_stats", "on_base_percentage")
    op.drop_column("pitching_stats", "caught_stealing")
    op.drop_column("pitching_stats", "ground_into_double_play")
    op.drop_column("pitching_stats", "sacrifice_flies")
    op.drop_column("pitching_stats", "sacrifice_bunts")
    op.drop_column("pitching_stats", "catchers_interference")
    op.drop_column("pitching_stats", "games_finished")
    op.drop_column("pitching_stats", "total_bases")
    op.drop_column("pitching_stats", "pickoffs")
    op.drop_column("pitching_stats", "strikes")
    op.drop_column("pitching_stats", "outs")
    op.drop_column("pitching_stats", "at_bats")
    op.drop_column("pitching_stats", "triples")
    op.drop_column("pitching_stats", "doubles")
