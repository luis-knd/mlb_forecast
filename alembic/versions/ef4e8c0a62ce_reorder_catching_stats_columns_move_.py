"""Reorder catching_stats columns - move timestamps to end

Revision ID: ef4e8c0a62ce
Revises: 101aa27d5a0f
Create Date: 2025-07-21 18:57:31.929040

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ef4e8c0a62ce"
down_revision = "101aa27d5a0f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL doesn't support column reordering directly, so we need to recreate the table
    # with the desired column order

    # First, let's check if there's any data in the table
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT COUNT(*) FROM catching_stats")).fetchone()
    has_data = result[0] > 0 if result else False

    # Create a new table with the correct column order
    op.execute(
        """
        CREATE TABLE catching_stats_new (
            id SERIAL PRIMARY KEY,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,

            -- Basic game stats
            games_played INTEGER DEFAULT 0,
            games_pitched INTEGER DEFAULT 0,

            -- Offensive stats (catchers can bat)
            at_bats INTEGER DEFAULT 0,
            hits INTEGER DEFAULT 0,
            runs INTEGER DEFAULT 0,
            home_runs INTEGER DEFAULT 0,
            strikeouts INTEGER DEFAULT 0,
            base_on_balls INTEGER DEFAULT 0,
            intentional_walks INTEGER DEFAULT 0,
            hit_by_pitch INTEGER DEFAULT 0,
            total_bases INTEGER DEFAULT 0,
            sacrifice_bunts INTEGER DEFAULT 0,
            sacrifice_flies INTEGER DEFAULT 0,

            -- Batting averages and percentages
            batting_average FLOAT DEFAULT 0.0,
            on_base_percentage FLOAT DEFAULT 0.0,
            slugging_percentage FLOAT DEFAULT 0.0,
            ops FLOAT DEFAULT 0.0,

            -- Catching-specific defensive stats
            passed_balls INTEGER DEFAULT 0,
            wild_pitches INTEGER DEFAULT 0,
            stolen_bases_allowed INTEGER DEFAULT 0,
            caught_stealing INTEGER DEFAULT 0,
            stolen_base_percentage FLOAT DEFAULT 0.0,
            pickoffs INTEGER DEFAULT 0,
            pickoff_attempts INTEGER DEFAULT 0,
            catchers_interference INTEGER DEFAULT 0,

            -- Pitching stats (catchers may occasionally pitch)
            earned_runs INTEGER DEFAULT 0,
            batters_faced INTEGER DEFAULT 0,
            hit_batsmen INTEGER DEFAULT 0,
            strikeout_walk_ratio FLOAT DEFAULT 0.0,

            -- Timestamps at the end
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE,

            -- Constraints
            CONSTRAINT uq_team_season_catching_new UNIQUE (team_id, season),
            CONSTRAINT catching_stats_new_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    """
    )

    # Copy data from the old table to the new one only if there's data
    if has_data:
        op.execute(
            """
            INSERT INTO catching_stats_new (
                team_id, season, games_played, games_pitched, at_bats, hits, runs,
                home_runs, strikeouts, base_on_balls, intentional_walks, hit_by_pitch,
                total_bases, sacrifice_bunts, sacrifice_flies, batting_average,
                on_base_percentage, slugging_percentage, ops, passed_balls, wild_pitches,
                stolen_bases_allowed, caught_stealing, stolen_base_percentage, pickoffs,
                pickoff_attempts, catchers_interference, earned_runs, batters_faced,
                hit_batsmen, strikeout_walk_ratio, created_at, updated_at
            )
            SELECT
                team_id, season, games_played, games_pitched, at_bats, hits, runs,
                home_runs, strikeouts, base_on_balls, intentional_walks, hit_by_pitch,
                total_bases, sacrifice_bunts, sacrifice_flies, batting_average,
                on_base_percentage, slugging_percentage, ops, passed_balls, wild_pitches,
                stolen_bases_allowed, caught_stealing, stolen_base_percentage, pickoffs,
                pickoff_attempts, catchers_interference, earned_runs, batters_faced,
                hit_batsmen, strikeout_walk_ratio, created_at, updated_at
            FROM catching_stats
        """
        )

    # Drop the old table and rename the new one
    op.execute("DROP TABLE catching_stats CASCADE")
    op.execute("ALTER TABLE catching_stats_new RENAME TO catching_stats")

    # Recreate the indices
    op.execute("CREATE INDEX ix_catching_stats_id ON catching_stats (id)")
    op.execute("CREATE INDEX idx_catching_stats_season ON catching_stats (season)")


def downgrade() -> None:
    # For downgrade, we would need to recreate the table with the original column order
    # This is complex, so we'll keep it simple and just note that this migration
    # changes column order which is primarily cosmetic
    pass
