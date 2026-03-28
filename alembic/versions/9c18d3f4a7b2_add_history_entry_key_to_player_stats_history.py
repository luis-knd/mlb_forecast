"""Add history entry key to player stats history

Revision ID: 9c18d3f4a7b2
Revises: f3c1d84a6b12
Create Date: 2026-03-28 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c18d3f4a7b2"
down_revision = "f3c1d84a6b12"
branch_labels = None
depends_on = None

OLD_HISTORY_CONTEXT_COLUMNS = ["player_id", "season", "game_type", "stat_group", "external_reference"]
NEW_HISTORY_CONTEXT_COLUMNS = ["player_id", "season", "game_type", "stat_group", "history_entry_key"]
HISTORY_TABLE_SPECS = (
    ("player_game_logs", "uq_player_game_logs_context", "gameLog"),
    ("player_stat_splits", "uq_player_stat_splits_context", "statSplits"),
)


def _backfill_history_entry_key(table_name: str, stat_type: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET history_entry_key = concat_ws(
                '|',
                :stat_type,
                external_reference,
                coalesce(context_key, '-'),
                coalesce(context_value, '-'),
                substring(md5(payload::text), 1, 16)
            )
            WHERE history_entry_key IS NULL
            """
        ).bindparams(stat_type=stat_type)
    )


def upgrade() -> None:
    for table_name, constraint_name, stat_type in HISTORY_TABLE_SPECS:
        op.add_column(table_name, sa.Column("history_entry_key", sa.String(length=255), nullable=True))
        _backfill_history_entry_key(table_name, stat_type)
        op.alter_column(table_name, "history_entry_key", existing_type=sa.String(length=255), nullable=False)
        op.drop_constraint(constraint_name, table_name, type_="unique")
        op.create_unique_constraint(constraint_name, table_name, NEW_HISTORY_CONTEXT_COLUMNS)


def downgrade() -> None:
    for table_name, constraint_name, _ in HISTORY_TABLE_SPECS:
        op.drop_constraint(constraint_name, table_name, type_="unique")
        op.create_unique_constraint(constraint_name, table_name, OLD_HISTORY_CONTEXT_COLUMNS)
        op.drop_column(table_name, "history_entry_key")
