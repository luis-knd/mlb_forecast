"""Drop legacy player_stats table.

Revision ID: 3e5c6a4b1d20
Revises: 9c18d3f4a7b2
Create Date: 2026-03-28 16:25:00.000000
"""

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3e5c6a4b1d20"
down_revision = "9c18d3f4a7b2"
branch_labels = None
depends_on = None

LEGACY_TABLE_NAME = "player_stats"
LEGACY_INDEXES = (
    "idx_player_stats_season",
    "idx_player_stats_team",
    "ix_player_stats_id",
)


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _existing_indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _drop_indexes_if_present(table_name: str, index_names: Iterable[str]) -> None:
    existing_indexes = _existing_indexes(table_name)
    for index_name in index_names:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    if not _table_exists(LEGACY_TABLE_NAME):
        return

    _drop_indexes_if_present(LEGACY_TABLE_NAME, LEGACY_INDEXES)
    op.drop_table(LEGACY_TABLE_NAME)


def downgrade() -> None:
    op.create_table(
        LEGACY_TABLE_NAME,
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("season", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("team_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("games_played", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("at_bats", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("hits", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("doubles", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("triples", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("home_runs", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("runs_batted_in", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("walks", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("strikeouts", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("batting_average", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column("on_base_percentage", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column("slugging_percentage", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column("innings_pitched", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column("earned_runs", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("earned_run_average", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column("wins", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("losses", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("saves", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("strikeouts_pitched", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("walks_allowed", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name="player_stats_player_id_fkey"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name="player_stats_team_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="player_stats_pkey"),
        sa.UniqueConstraint("player_id", "season", "team_id", name="uq_player_season_team"),
    )
    op.create_index("ix_player_stats_id", LEGACY_TABLE_NAME, ["id"], unique=False)
    op.create_index("idx_player_stats_team", LEGACY_TABLE_NAME, ["team_id", "season"], unique=False)
    op.create_index("idx_player_stats_season", LEGACY_TABLE_NAME, ["season"], unique=False)
