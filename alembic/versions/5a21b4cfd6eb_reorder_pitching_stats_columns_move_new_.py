"""Reorder pitching_stats columns move new fields before timestamps

Revision ID: 5a21b4cfd6eb
Revises: 8a9b3523afe7
Create Date: 2025-07-24 17:38:31.404499

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5a21b4cfd6eb"
down_revision = "8a9b3523afe7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Reorder pitching_stats columns to place new fields before created_at and updated_at."""

    # First, drop existing constraints and indexes that will conflict
    op.drop_constraint("uq_team_season_pitching", "pitching_stats", type_="unique")
    op.drop_index("idx_pitching_stats_season", table_name="pitching_stats")

    # Create a new table with the correct column order
    op.create_table(
        "pitching_stats_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        # Basic stats
        sa.Column("games_played", sa.Integer(), default=0),
        sa.Column("wins", sa.Integer(), default=0),
        sa.Column("losses", sa.Integer(), default=0),
        sa.Column("saves", sa.Integer(), default=0),
        sa.Column("save_opportunities", sa.Integer(), default=0),
        sa.Column("holds", sa.Integer(), default=0),
        sa.Column("blown_saves", sa.Integer(), default=0),
        sa.Column("innings_pitched", sa.Float(), default=0.0),
        sa.Column("batters_faced", sa.Integer(), default=0),
        sa.Column("hits_allowed", sa.Integer(), default=0),
        sa.Column("runs_allowed", sa.Integer(), default=0),
        sa.Column("earned_runs", sa.Integer(), default=0),
        sa.Column("home_runs_allowed", sa.Integer(), default=0),
        sa.Column("strikeouts", sa.Integer(), default=0),
        sa.Column("base_on_balls", sa.Integer(), default=0),
        sa.Column("intentional_walks", sa.Integer(), default=0),
        sa.Column("hit_batsmen", sa.Integer(), default=0),
        sa.Column("wild_pitches", sa.Integer(), default=0),
        sa.Column("balks", sa.Integer(), default=0),
        sa.Column("number_of_pitches", sa.Integer(), default=0),
        sa.Column("complete_games", sa.Integer(), default=0),
        sa.Column("shutouts", sa.Integer(), default=0),
        sa.Column("games_started", sa.Integer(), default=0),
        sa.Column("ground_outs", sa.Integer(), default=0),
        sa.Column("air_outs", sa.Integer(), default=0),
        # Additional basic stats from MLB API (positioned before advanced stats)
        sa.Column("doubles", sa.Integer(), default=0),
        sa.Column("triples", sa.Integer(), default=0),
        sa.Column("at_bats", sa.Integer(), default=0),
        sa.Column("outs", sa.Integer(), default=0),
        sa.Column("strikes", sa.Integer(), default=0),
        sa.Column("pickoffs", sa.Integer(), default=0),
        sa.Column("total_bases", sa.Integer(), default=0),
        sa.Column("games_finished", sa.Integer(), default=0),
        sa.Column("catchers_interference", sa.Integer(), default=0),
        sa.Column("sacrifice_bunts", sa.Integer(), default=0),
        sa.Column("sacrifice_flies", sa.Integer(), default=0),
        sa.Column("ground_into_double_play", sa.Integer(), default=0),
        sa.Column("caught_stealing", sa.Integer(), default=0),
        # Advanced stats
        sa.Column("earned_run_average", sa.Float(), default=0.0),
        sa.Column("whip", sa.Float(), default=0.0),
        sa.Column("strikeouts_per_nine", sa.Float(), default=0.0),
        sa.Column("walks_per_nine", sa.Float(), default=0.0),
        sa.Column("hits_per_nine", sa.Float(), default=0.0),
        sa.Column("home_runs_per_nine", sa.Float(), default=0.0),
        sa.Column("strikeout_to_walk_ratio", sa.Float(), default=0.0),
        sa.Column("ground_outs_to_airouts", sa.Float(), default=0.0),
        sa.Column("pitches_per_inning", sa.Float(), default=0.0),
        sa.Column("batting_average_against", sa.Float(), default=0.0),
        sa.Column("inherited_runners", sa.Integer(), default=0),
        sa.Column("inherited_runners_scored", sa.Integer(), default=0),
        sa.Column("quality_starts", sa.Integer(), default=0),
        # Additional advanced stats from MLB API (positioned before timestamps)
        sa.Column("on_base_percentage", sa.Float(), default=0.0),
        sa.Column("slugging_percentage", sa.Float(), default=0.0),
        sa.Column("ops", sa.Float(), default=0.0),
        sa.Column("stolen_base_percentage", sa.Float(), default=0.0),
        sa.Column("strike_percentage", sa.Float(), default=0.0),
        sa.Column("win_percentage", sa.Float(), default=0.0),
        sa.Column("runs_scored_per_nine", sa.Float(), default=0.0),
        # Timestamps (MUST BE LAST)
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
    )

    # Copy data from old table to new table with explicit column mapping
    op.execute(
        """
        INSERT INTO pitching_stats_new (
            id, team_id, season, games_played, wins, losses, saves, save_opportunities,
            holds, blown_saves, innings_pitched, batters_faced, hits_allowed, runs_allowed,
            earned_runs, home_runs_allowed, strikeouts, base_on_balls, intentional_walks,
            hit_batsmen, wild_pitches, balks, number_of_pitches, complete_games, shutouts,
            games_started, ground_outs, air_outs, doubles, triples, at_bats, outs, strikes,
            pickoffs, total_bases, games_finished, catchers_interference, sacrifice_bunts,
            sacrifice_flies, ground_into_double_play, caught_stealing, earned_run_average,
            whip, strikeouts_per_nine, walks_per_nine, hits_per_nine, home_runs_per_nine,
            strikeout_to_walk_ratio, ground_outs_to_airouts, pitches_per_inning,
            batting_average_against, inherited_runners, inherited_runners_scored,
            quality_starts, on_base_percentage, slugging_percentage, ops,
            stolen_base_percentage, strike_percentage, win_percentage, runs_scored_per_nine,
            created_at, updated_at
        )
        SELECT
            id, team_id, season, games_played, wins, losses, saves, save_opportunities,
            holds, blown_saves, innings_pitched, batters_faced, hits_allowed, runs_allowed,
            earned_runs, home_runs_allowed, strikeouts, base_on_balls, intentional_walks,
            hit_batsmen, wild_pitches, balks, number_of_pitches, complete_games, shutouts,
            games_started, ground_outs, air_outs, doubles, triples, at_bats, outs, strikes,
            pickoffs, total_bases, games_finished, catchers_interference, sacrifice_bunts,
            sacrifice_flies, ground_into_double_play, caught_stealing, earned_run_average,
            whip, strikeouts_per_nine, walks_per_nine, hits_per_nine, home_runs_per_nine,
            strikeout_to_walk_ratio, ground_outs_to_airouts, pitches_per_inning,
            batting_average_against, inherited_runners, inherited_runners_scored,
            quality_starts, on_base_percentage, slugging_percentage, ops,
            stolen_base_percentage, strike_percentage, win_percentage, runs_scored_per_nine,
            created_at, updated_at
        FROM pitching_stats
    """
    )

    # Drop the old table
    op.drop_table("pitching_stats")

    # Rename the new table to the original name
    op.rename_table("pitching_stats_new", "pitching_stats")

    # Recreate constraints and indexes with proper names
    op.create_unique_constraint("uq_team_season_pitching", "pitching_stats", ["team_id", "season"])
    op.create_index("idx_pitching_stats_season", "pitching_stats", ["season"])


def downgrade() -> None:
    """Revert the column reordering by recreating the table with original order."""

    # Drop existing constraints and indexes
    op.drop_constraint("uq_team_season_pitching", "pitching_stats", type_="unique")
    op.drop_index("idx_pitching_stats_season", table_name="pitching_stats")

    # Create a table with the original column order (timestamps before new fields)
    op.create_table(
        "pitching_stats_old",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("games_played", sa.Integer(), default=0),
        sa.Column("wins", sa.Integer(), default=0),
        sa.Column("losses", sa.Integer(), default=0),
        sa.Column("saves", sa.Integer(), default=0),
        sa.Column("save_opportunities", sa.Integer(), default=0),
        sa.Column("holds", sa.Integer(), default=0),
        sa.Column("blown_saves", sa.Integer(), default=0),
        sa.Column("innings_pitched", sa.Float(), default=0.0),
        sa.Column("batters_faced", sa.Integer(), default=0),
        sa.Column("hits_allowed", sa.Integer(), default=0),
        sa.Column("runs_allowed", sa.Integer(), default=0),
        sa.Column("earned_runs", sa.Integer(), default=0),
        sa.Column("home_runs_allowed", sa.Integer(), default=0),
        sa.Column("strikeouts", sa.Integer(), default=0),
        sa.Column("base_on_balls", sa.Integer(), default=0),
        sa.Column("intentional_walks", sa.Integer(), default=0),
        sa.Column("hit_batsmen", sa.Integer(), default=0),
        sa.Column("wild_pitches", sa.Integer(), default=0),
        sa.Column("balks", sa.Integer(), default=0),
        sa.Column("number_of_pitches", sa.Integer(), default=0),
        sa.Column("complete_games", sa.Integer(), default=0),
        sa.Column("shutouts", sa.Integer(), default=0),
        sa.Column("games_started", sa.Integer(), default=0),
        sa.Column("ground_outs", sa.Integer(), default=0),
        sa.Column("air_outs", sa.Integer(), default=0),
        sa.Column("earned_run_average", sa.Float(), default=0.0),
        sa.Column("whip", sa.Float(), default=0.0),
        sa.Column("strikeouts_per_nine", sa.Float(), default=0.0),
        sa.Column("walks_per_nine", sa.Float(), default=0.0),
        sa.Column("hits_per_nine", sa.Float(), default=0.0),
        sa.Column("home_runs_per_nine", sa.Float(), default=0.0),
        sa.Column("strikeout_to_walk_ratio", sa.Float(), default=0.0),
        sa.Column("ground_outs_to_airouts", sa.Float(), default=0.0),
        sa.Column("pitches_per_inning", sa.Float(), default=0.0),
        sa.Column("batting_average_against", sa.Float(), default=0.0),
        sa.Column("inherited_runners", sa.Integer(), default=0),
        sa.Column("inherited_runners_scored", sa.Integer(), default=0),
        sa.Column("quality_starts", sa.Integer(), default=0),
        # Original timestamps position
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        # New fields at the end (original incorrect position)
        sa.Column("doubles", sa.Integer(), default=0),
        sa.Column("triples", sa.Integer(), default=0),
        sa.Column("at_bats", sa.Integer(), default=0),
        sa.Column("outs", sa.Integer(), default=0),
        sa.Column("strikes", sa.Integer(), default=0),
        sa.Column("pickoffs", sa.Integer(), default=0),
        sa.Column("total_bases", sa.Integer(), default=0),
        sa.Column("games_finished", sa.Integer(), default=0),
        sa.Column("catchers_interference", sa.Integer(), default=0),
        sa.Column("sacrifice_bunts", sa.Integer(), default=0),
        sa.Column("sacrifice_flies", sa.Integer(), default=0),
        sa.Column("ground_into_double_play", sa.Integer(), default=0),
        sa.Column("caught_stealing", sa.Integer(), default=0),
        sa.Column("on_base_percentage", sa.Float(), default=0.0),
        sa.Column("slugging_percentage", sa.Float(), default=0.0),
        sa.Column("ops", sa.Float(), default=0.0),
        sa.Column("stolen_base_percentage", sa.Float(), default=0.0),
        sa.Column("strike_percentage", sa.Float(), default=0.0),
        sa.Column("win_percentage", sa.Float(), default=0.0),
        sa.Column("runs_scored_per_nine", sa.Float(), default=0.0),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
    )

    # Copy data back with explicit column mapping
    op.execute(
        """
        INSERT INTO pitching_stats_old (
            id, team_id, season, games_played, wins, losses, saves, save_opportunities,
            holds, blown_saves, innings_pitched, batters_faced, hits_allowed, runs_allowed,
            earned_runs, home_runs_allowed, strikeouts, base_on_balls, intentional_walks,
            hit_batsmen, wild_pitches, balks, number_of_pitches, complete_games, shutouts,
            games_started, ground_outs, air_outs, earned_run_average, whip, strikeouts_per_nine,
            walks_per_nine, hits_per_nine, home_runs_per_nine, strikeout_to_walk_ratio,
            ground_outs_to_airouts, pitches_per_inning, batting_average_against,
            inherited_runners, inherited_runners_scored, quality_starts, created_at, updated_at,
            doubles, triples, at_bats, outs, strikes, pickoffs, total_bases, games_finished,
            catchers_interference, sacrifice_bunts, sacrifice_flies, ground_into_double_play,
            caught_stealing, on_base_percentage, slugging_percentage, ops, stolen_base_percentage,
            strike_percentage, win_percentage, runs_scored_per_nine
        )
        SELECT
            id, team_id, season, games_played, wins, losses, saves, save_opportunities,
            holds, blown_saves, innings_pitched, batters_faced, hits_allowed, runs_allowed,
            earned_runs, home_runs_allowed, strikeouts, base_on_balls, intentional_walks,
            hit_batsmen, wild_pitches, balks, number_of_pitches, complete_games, shutouts,
            games_started, ground_outs, air_outs, earned_run_average, whip, strikeouts_per_nine,
            walks_per_nine, hits_per_nine, home_runs_per_nine, strikeout_to_walk_ratio,
            ground_outs_to_airouts, pitches_per_inning, batting_average_against,
            inherited_runners, inherited_runners_scored, quality_starts, created_at, updated_at,
            doubles, triples, at_bats, outs, strikes, pickoffs, total_bases, games_finished,
            catchers_interference, sacrifice_bunts, sacrifice_flies, ground_into_double_play,
            caught_stealing, on_base_percentage, slugging_percentage, ops, stolen_base_percentage,
            strike_percentage, win_percentage, runs_scored_per_nine
        FROM pitching_stats
    """
    )

    # Drop and rename
    op.drop_table("pitching_stats")
    op.rename_table("pitching_stats_old", "pitching_stats")

    # Recreate constraints and indexes
    op.create_unique_constraint("uq_team_season_pitching", "pitching_stats", ["team_id", "season"])
    op.create_index("idx_pitching_stats_season", "pitching_stats", ["season"])
