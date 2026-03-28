"""Add player stats persistence tables

Revision ID: f3c1d84a6b12
Revises: b652ea929021
Create Date: 2026-03-21 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "f3c1d84a6b12"
down_revision = "b652ea929021"
branch_labels = None
depends_on = None

AGGREGATE_CONTEXT_COLUMNS = ["player_id", "team_id", "season", "game_type"]
HISTORY_CONTEXT_COLUMNS = ["player_id", "season", "game_type", "stat_group", "external_reference"]


def _metadata_columns(team_nullable: bool = False) -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=team_nullable),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("game_type", sa.String(length=5), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _history_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("game_type", sa.String(length=5), nullable=False),
        sa.Column("stat_group", sa.String(length=20), nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("context_key", sa.String(length=64), nullable=True),
        sa.Column("context_value", sa.String(length=128), nullable=True),
        sa.Column("context_label", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _get_inspector() -> Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(inspector: Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _existing_index_names(inspector: Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _existing_unique_constraint_names(inspector: Inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str], inspector: Inspector) -> None:
    if index_name not in _existing_index_names(inspector, table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def _create_unique_constraint_if_missing(
    table_name: str,
    constraint_name: str,
    columns: list[str],
    inspector: Inspector,
) -> None:
    if constraint_name not in _existing_unique_constraint_names(inspector, table_name):
        op.create_unique_constraint(constraint_name, table_name, columns)


def _drop_index_if_exists(table_name: str, index_name: str, inspector: Inspector) -> None:
    if index_name in _existing_index_names(inspector, table_name):
        op.drop_index(index_name, table_name=table_name)


def _create_aggregate_table(table_name: str, extra_columns: list[sa.Column], unique_name: str) -> None:
    inspector = _get_inspector()
    if _table_exists(inspector, table_name):
        _create_unique_constraint_if_missing(table_name, unique_name, AGGREGATE_CONTEXT_COLUMNS, inspector)
        _create_index_if_missing(table_name, f"ix_{table_name}_id", ["id"], inspector)
        _create_index_if_missing(table_name, f"idx_{table_name}_player_season", ["player_id", "season"], inspector)
        _create_index_if_missing(table_name, f"idx_{table_name}_player_group", ["player_id", "game_type"], inspector)
        return

    op.create_table(
        table_name,
        *_metadata_columns(),
        *extra_columns,
        sa.UniqueConstraint("player_id", "team_id", "season", "game_type", name=unique_name),
    )
    op.create_index(f"ix_{table_name}_id", table_name, ["id"], unique=False)
    op.create_index(f"idx_{table_name}_player_season", table_name, ["player_id", "season"], unique=False)
    op.create_index(f"idx_{table_name}_player_group", table_name, ["player_id", "game_type"], unique=False)


def _drop_aggregate_table(table_name: str) -> None:
    inspector = _get_inspector()
    if not _table_exists(inspector, table_name):
        return
    _drop_index_if_exists(table_name, f"idx_{table_name}_player_group", inspector)
    _drop_index_if_exists(table_name, f"idx_{table_name}_player_season", inspector)
    _drop_index_if_exists(table_name, f"ix_{table_name}_id", inspector)
    op.drop_table(table_name)


def _create_history_table(table_name: str, unique_name: str, extra_indexes: list[tuple[str, list[str]]]) -> None:
    inspector = _get_inspector()
    if _table_exists(inspector, table_name):
        _create_unique_constraint_if_missing(table_name, unique_name, HISTORY_CONTEXT_COLUMNS, inspector)
        _create_index_if_missing(table_name, f"ix_{table_name}_id", ["id"], inspector)
        _create_index_if_missing(table_name, f"idx_{table_name}_player_season", ["player_id", "season"], inspector)
        _create_index_if_missing(table_name, f"idx_{table_name}_player_group", ["player_id", "stat_group"], inspector)
        for index_name, columns in extra_indexes:
            _create_index_if_missing(table_name, index_name, columns, inspector)
        return

    op.create_table(
        table_name,
        *_history_columns(),
        sa.UniqueConstraint(
            "player_id",
            "season",
            "game_type",
            "stat_group",
            "external_reference",
            name=unique_name,
        ),
    )
    op.create_index(f"ix_{table_name}_id", table_name, ["id"], unique=False)
    op.create_index(f"idx_{table_name}_player_season", table_name, ["player_id", "season"], unique=False)
    op.create_index(f"idx_{table_name}_player_group", table_name, ["player_id", "stat_group"], unique=False)
    for index_name, columns in extra_indexes:
        op.create_index(index_name, table_name, columns, unique=False)


def _drop_history_table(table_name: str, extra_index_names: list[str]) -> None:
    inspector = _get_inspector()
    if not _table_exists(inspector, table_name):
        return
    for index_name in extra_index_names:
        _drop_index_if_exists(table_name, index_name, inspector)
    _drop_index_if_exists(table_name, f"idx_{table_name}_player_group", inspector)
    _drop_index_if_exists(table_name, f"idx_{table_name}_player_season", inspector)
    _drop_index_if_exists(table_name, f"ix_{table_name}_id", inspector)
    op.drop_table(table_name)


def upgrade() -> None:
    _create_aggregate_table(
        "player_hitting_stats",
        [
            sa.Column("games_played", sa.Integer(), nullable=True),
            sa.Column("at_bats", sa.Integer(), nullable=True),
            sa.Column("plate_appearances", sa.Integer(), nullable=True),
            sa.Column("hits", sa.Integer(), nullable=True),
            sa.Column("doubles", sa.Integer(), nullable=True),
            sa.Column("triples", sa.Integer(), nullable=True),
            sa.Column("home_runs", sa.Integer(), nullable=True),
            sa.Column("runs_scored", sa.Integer(), nullable=True),
            sa.Column("runs_batted_in", sa.Integer(), nullable=True),
            sa.Column("stolen_bases", sa.Integer(), nullable=True),
            sa.Column("caught_stealing", sa.Integer(), nullable=True),
            sa.Column("base_on_balls", sa.Integer(), nullable=True),
            sa.Column("strikeouts", sa.Integer(), nullable=True),
            sa.Column("hit_by_pitch", sa.Integer(), nullable=True),
            sa.Column("sacrifice_hits", sa.Integer(), nullable=True),
            sa.Column("sacrifice_flies", sa.Integer(), nullable=True),
            sa.Column("left_on_base", sa.Integer(), nullable=True),
            sa.Column("intentional_walks", sa.Integer(), nullable=True),
            sa.Column("total_bases", sa.Integer(), nullable=True),
            sa.Column("batting_average", sa.Float(), nullable=True),
            sa.Column("on_base_percentage", sa.Float(), nullable=True),
            sa.Column("slugging_percentage", sa.Float(), nullable=True),
            sa.Column("ops", sa.Float(), nullable=True),
            sa.Column("babip", sa.Float(), nullable=True),
            sa.Column("at_bats_per_home_run", sa.Float(), nullable=True),
            sa.Column("stolen_base_percentage", sa.Float(), nullable=True),
        ],
        "uq_player_hitting_stats_context",
    )

    _create_aggregate_table(
        "player_pitching_stats",
        [
            sa.Column("games_played", sa.Integer(), nullable=True),
            sa.Column("games_started", sa.Integer(), nullable=True),
            sa.Column("wins", sa.Integer(), nullable=True),
            sa.Column("losses", sa.Integer(), nullable=True),
            sa.Column("saves", sa.Integer(), nullable=True),
            sa.Column("save_opportunities", sa.Integer(), nullable=True),
            sa.Column("holds", sa.Integer(), nullable=True),
            sa.Column("blown_saves", sa.Integer(), nullable=True),
            sa.Column("innings_pitched", sa.Float(), nullable=True),
            sa.Column("batters_faced", sa.Integer(), nullable=True),
            sa.Column("hits_allowed", sa.Integer(), nullable=True),
            sa.Column("runs_allowed", sa.Integer(), nullable=True),
            sa.Column("earned_runs", sa.Integer(), nullable=True),
            sa.Column("home_runs_allowed", sa.Integer(), nullable=True),
            sa.Column("strikeouts", sa.Integer(), nullable=True),
            sa.Column("base_on_balls", sa.Integer(), nullable=True),
            sa.Column("intentional_walks", sa.Integer(), nullable=True),
            sa.Column("hit_batsmen", sa.Integer(), nullable=True),
            sa.Column("wild_pitches", sa.Integer(), nullable=True),
            sa.Column("balks", sa.Integer(), nullable=True),
            sa.Column("number_of_pitches", sa.Integer(), nullable=True),
            sa.Column("complete_games", sa.Integer(), nullable=True),
            sa.Column("shutouts", sa.Integer(), nullable=True),
            sa.Column("outs", sa.Integer(), nullable=True),
            sa.Column("strikes", sa.Integer(), nullable=True),
            sa.Column("pickoffs", sa.Integer(), nullable=True),
            sa.Column("quality_starts", sa.Integer(), nullable=True),
            sa.Column("earned_run_average", sa.Float(), nullable=True),
            sa.Column("whip", sa.Float(), nullable=True),
            sa.Column("strikeouts_per_nine", sa.Float(), nullable=True),
            sa.Column("walks_per_nine", sa.Float(), nullable=True),
            sa.Column("hits_per_nine", sa.Float(), nullable=True),
            sa.Column("home_runs_per_nine", sa.Float(), nullable=True),
            sa.Column("strikeout_to_walk_ratio", sa.Float(), nullable=True),
            sa.Column("pitches_per_inning", sa.Float(), nullable=True),
            sa.Column("batting_average_against", sa.Float(), nullable=True),
            sa.Column("on_base_percentage", sa.Float(), nullable=True),
            sa.Column("slugging_percentage", sa.Float(), nullable=True),
            sa.Column("ops", sa.Float(), nullable=True),
            sa.Column("strike_percentage", sa.Float(), nullable=True),
            sa.Column("win_percentage", sa.Float(), nullable=True),
        ],
        "uq_player_pitching_stats_context",
    )

    _create_aggregate_table(
        "player_fielding_stats",
        [
            sa.Column("games_played", sa.Integer(), nullable=True),
            sa.Column("games_started", sa.Integer(), nullable=True),
            sa.Column("innings_played", sa.Float(), nullable=True),
            sa.Column("total_chances", sa.Integer(), nullable=True),
            sa.Column("putouts", sa.Integer(), nullable=True),
            sa.Column("assists", sa.Integer(), nullable=True),
            sa.Column("errors", sa.Integer(), nullable=True),
            sa.Column("throwing_errors", sa.Integer(), nullable=True),
            sa.Column("double_plays", sa.Integer(), nullable=True),
            sa.Column("triple_plays", sa.Integer(), nullable=True),
            sa.Column("outfield_assists", sa.Integer(), nullable=True),
            sa.Column("passed_balls", sa.Integer(), nullable=True),
            sa.Column("wild_pitches", sa.Integer(), nullable=True),
            sa.Column("stolen_bases_allowed", sa.Integer(), nullable=True),
            sa.Column("caught_stealing", sa.Integer(), nullable=True),
            sa.Column("catchers_interference", sa.Integer(), nullable=True),
            sa.Column("pickoffs", sa.Integer(), nullable=True),
            sa.Column("fielding_percentage", sa.Float(), nullable=True),
            sa.Column("defensive_efficiency_ratio", sa.Float(), nullable=True),
            sa.Column("range_factor_per_game", sa.Float(), nullable=True),
            sa.Column("range_factor_per_nine", sa.Float(), nullable=True),
            sa.Column("stolen_base_percentage", sa.Float(), nullable=True),
        ],
        "uq_player_fielding_stats_context",
    )

    _create_aggregate_table(
        "player_catching_stats",
        [
            sa.Column("games_played", sa.Integer(), nullable=True),
            sa.Column("games_pitched", sa.Integer(), nullable=True),
            sa.Column("at_bats", sa.Integer(), nullable=True),
            sa.Column("hits", sa.Integer(), nullable=True),
            sa.Column("runs", sa.Integer(), nullable=True),
            sa.Column("home_runs", sa.Integer(), nullable=True),
            sa.Column("strikeouts", sa.Integer(), nullable=True),
            sa.Column("base_on_balls", sa.Integer(), nullable=True),
            sa.Column("intentional_walks", sa.Integer(), nullable=True),
            sa.Column("hit_by_pitch", sa.Integer(), nullable=True),
            sa.Column("total_bases", sa.Integer(), nullable=True),
            sa.Column("sacrifice_bunts", sa.Integer(), nullable=True),
            sa.Column("sacrifice_flies", sa.Integer(), nullable=True),
            sa.Column("passed_balls", sa.Integer(), nullable=True),
            sa.Column("wild_pitches", sa.Integer(), nullable=True),
            sa.Column("stolen_bases_allowed", sa.Integer(), nullable=True),
            sa.Column("caught_stealing", sa.Integer(), nullable=True),
            sa.Column("pickoffs", sa.Integer(), nullable=True),
            sa.Column("pickoff_attempts", sa.Integer(), nullable=True),
            sa.Column("catchers_interference", sa.Integer(), nullable=True),
            sa.Column("earned_runs", sa.Integer(), nullable=True),
            sa.Column("batters_faced", sa.Integer(), nullable=True),
            sa.Column("hit_batsmen", sa.Integer(), nullable=True),
            sa.Column("batting_average", sa.Float(), nullable=True),
            sa.Column("on_base_percentage", sa.Float(), nullable=True),
            sa.Column("slugging_percentage", sa.Float(), nullable=True),
            sa.Column("ops", sa.Float(), nullable=True),
            sa.Column("stolen_base_percentage", sa.Float(), nullable=True),
            sa.Column("strikeout_walk_ratio", sa.Float(), nullable=True),
        ],
        "uq_player_catching_stats_context",
    )

    _create_aggregate_table(
        "player_running_stats",
        [
            sa.Column("games_played", sa.Integer(), nullable=True),
            sa.Column("plate_appearances", sa.Integer(), nullable=True),
            sa.Column("stolen_bases", sa.Integer(), nullable=True),
            sa.Column("stolen_base_percentage", sa.Float(), nullable=True),
            sa.Column("caught_stealing", sa.Integer(), nullable=True),
            sa.Column("runs", sa.Integer(), nullable=True),
            sa.Column("base_on_balls", sa.Integer(), nullable=True),
            sa.Column("opportunities", sa.Integer(), nullable=True),
        ],
        "uq_player_running_stats_context",
    )

    _create_history_table(
        "player_game_logs",
        "uq_player_game_logs_context",
        [("idx_player_game_logs_event_date", ["event_date"])],
    )
    _create_history_table(
        "player_stat_splits",
        "uq_player_stat_splits_context",
        [("idx_player_stat_splits_context", ["context_key", "context_value"])],
    )


def downgrade() -> None:
    _drop_history_table("player_stat_splits", ["idx_player_stat_splits_context"])
    _drop_history_table("player_game_logs", ["idx_player_game_logs_event_date"])
    _drop_aggregate_table("player_running_stats")
    _drop_aggregate_table("player_catching_stats")
    _drop_aggregate_table("player_fielding_stats")
    _drop_aggregate_table("player_pitching_stats")
    _drop_aggregate_table("player_hitting_stats")
