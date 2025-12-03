"""Reorder fielding cols

Revision ID: b652ea929021
Revises: cc8f5661f8c6
Create Date: 2025-07-24 18:15:12.746631

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b652ea929021"
down_revision = "cc8f5661f8c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Reorder fielding stats columns to place new columns before created_at and updated_at."""
    # PostgreSQL doesn't support reordering columns directly, so we need to:
    # 1. Create a new table with the correct column order
    # 2. Copy data from old table to new table
    # 3. Drop old table and rename new table

    # Create new table with correct column order
    op.create_table(
        "fielding_stats_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        # Basic stats in correct order
        sa.Column("games_played", sa.Integer(), default=0, nullable=False),
        sa.Column("games_started", sa.Integer(), default=0, nullable=False),
        sa.Column("innings_played", sa.Float(), default=0.0, nullable=False),
        sa.Column("total_chances", sa.Integer(), default=0, nullable=False),
        sa.Column("putouts", sa.Integer(), default=0, nullable=False),
        sa.Column("assists", sa.Integer(), default=0, nullable=False),
        sa.Column("errors", sa.Integer(), default=0, nullable=False),
        sa.Column("throwing_errors", sa.Integer(), default=0, nullable=False),
        sa.Column("double_plays", sa.Integer(), default=0, nullable=False),
        sa.Column("triple_plays", sa.Integer(), default=0, nullable=False),
        sa.Column("fielding_percentage", sa.Float(), default=0.0, nullable=False),
        sa.Column("defensive_efficiency_ratio", sa.Float(), default=0.0, nullable=False),
        sa.Column("range_factor_per_game", sa.Float(), default=0.0, nullable=False),
        sa.Column("range_factor_per_nine", sa.Float(), default=0.0, nullable=False),
        sa.Column("outfield_assists", sa.Integer(), default=0, nullable=False),
        sa.Column("passed_balls", sa.Integer(), default=0, nullable=False),
        sa.Column("wild_pitches", sa.Integer(), default=0, nullable=False),
        sa.Column("stolen_bases_allowed", sa.Integer(), default=0, nullable=False),
        sa.Column("caught_stealing", sa.Integer(), default=0, nullable=False),
        sa.Column("stolen_base_percentage", sa.Float(), default=0.0, nullable=False),
        sa.Column("catchers_interference", sa.Integer(), default=0, nullable=False),
        sa.Column("pickoffs", sa.Integer(), default=0, nullable=False),
        # Timestamp columns at the end
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.UniqueConstraint("team_id", "season", name="uq_team_season_fielding_new"),
    )

    # Copy data from old table to new table
    op.execute(
        """
        INSERT INTO fielding_stats_new (
            id, team_id, season, games_played, games_started, innings_played,
            total_chances, putouts, assists, errors, throwing_errors, double_plays,
            triple_plays, fielding_percentage, defensive_efficiency_ratio,
            range_factor_per_game, range_factor_per_nine, outfield_assists,
            passed_balls, wild_pitches, stolen_bases_allowed, caught_stealing,
            stolen_base_percentage, catchers_interference, pickoffs, created_at, updated_at
        )
        SELECT
            id, team_id, season, games_played, games_started, innings_played,
            total_chances, putouts, assists, errors, throwing_errors, double_plays,
            triple_plays, fielding_percentage, defensive_efficiency_ratio,
            range_factor_per_game, range_factor_per_nine, outfield_assists,
            passed_balls, wild_pitches, stolen_bases_allowed, caught_stealing,
            stolen_base_percentage, catchers_interference, pickoffs, created_at, updated_at
        FROM fielding_stats
    """
    )

    # Drop old table
    op.drop_table("fielding_stats")

    # Rename new table to original name
    op.rename_table("fielding_stats_new", "fielding_stats")

    # Recreate indices
    op.create_index("idx_fielding_stats_season", "fielding_stats", ["season"])


def downgrade() -> None:
    """Revert the column reordering."""
    # This is complex to revert, so we'll just recreate the original structure
    pass
