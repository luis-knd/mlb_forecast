import importlib.util
from pathlib import Path
from unittest.mock import Mock, call


def _load_migration_module():
    module_path = (
        Path(__file__).resolve().parents[4]
        / "alembic"
        / "versions"
        / "f3c1d84a6b12_add_player_stats_persistence_tables.py"
    )
    spec = importlib.util.spec_from_file_location("player_stats_persistence_migration", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration_module()


class FakeInspector:
    def __init__(
        self,
        *,
        tables: set[str] | None = None,
        indexes: dict[str, set[str]] | None = None,
        unique_constraints: dict[str, set[str]] | None = None,
    ) -> None:
        self.tables = tables or set()
        self.indexes = indexes or {}
        self.unique_constraints = unique_constraints or {}

    def get_table_names(self) -> list[str]:
        return sorted(self.tables)

    def get_indexes(self, table_name: str) -> list[dict[str, str]]:
        return [{"name": index_name} for index_name in sorted(self.indexes.get(table_name, set()))]

    def get_unique_constraints(self, table_name: str) -> list[dict[str, str]]:
        return [{"name": constraint_name} for constraint_name in sorted(self.unique_constraints.get(table_name, set()))]


def _patch_migration(monkeypatch, inspector: FakeInspector) -> Mock:
    operation_proxy = Mock()
    operation_proxy.get_bind.return_value = object()
    monkeypatch.setattr(migration, "op", operation_proxy)
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)
    return operation_proxy


def test_create_aggregate_table_creates_missing_table(monkeypatch):
    # Given
    operation_proxy = _patch_migration(monkeypatch, FakeInspector())

    # When
    migration._create_aggregate_table("player_hitting_stats", [], "uq_player_hitting_stats_context")

    # Then
    operation_proxy.create_table.assert_called_once()
    assert operation_proxy.create_index.call_args_list == [
        call("ix_player_hitting_stats_id", "player_hitting_stats", ["id"], unique=False),
        call("idx_player_hitting_stats_player_season", "player_hitting_stats", ["player_id", "season"], unique=False),
        call("idx_player_hitting_stats_player_group", "player_hitting_stats", ["player_id", "game_type"], unique=False),
    ]
    operation_proxy.create_unique_constraint.assert_not_called()


def test_create_aggregate_table_repairs_existing_table_without_recreating_it(monkeypatch):
    # Given
    inspector = FakeInspector(tables={"player_hitting_stats"})
    operation_proxy = _patch_migration(monkeypatch, inspector)

    # When
    migration._create_aggregate_table("player_hitting_stats", [], "uq_player_hitting_stats_context")

    # Then
    operation_proxy.create_table.assert_not_called()
    operation_proxy.create_unique_constraint.assert_called_once_with(
        "uq_player_hitting_stats_context",
        "player_hitting_stats",
        ["player_id", "team_id", "season", "game_type"],
    )
    assert operation_proxy.create_index.call_args_list == [
        call("ix_player_hitting_stats_id", "player_hitting_stats", ["id"], unique=False),
        call("idx_player_hitting_stats_player_season", "player_hitting_stats", ["player_id", "season"], unique=False),
        call("idx_player_hitting_stats_player_group", "player_hitting_stats", ["player_id", "game_type"], unique=False),
    ]


def test_create_history_table_repairs_only_missing_constraints_and_indexes(monkeypatch):
    # Given
    inspector = FakeInspector(
        tables={"player_game_logs"},
        indexes={"player_game_logs": {"ix_player_game_logs_id"}},
        unique_constraints={"player_game_logs": {"uq_player_game_logs_context"}},
    )
    operation_proxy = _patch_migration(monkeypatch, inspector)

    # When
    migration._create_history_table(
        "player_game_logs",
        "uq_player_game_logs_context",
        [("idx_player_game_logs_event_date", ["event_date"])],
    )

    # Then
    operation_proxy.create_table.assert_not_called()
    operation_proxy.create_unique_constraint.assert_not_called()
    assert operation_proxy.create_index.call_args_list == [
        call("idx_player_game_logs_player_season", "player_game_logs", ["player_id", "season"], unique=False),
        call("idx_player_game_logs_player_group", "player_game_logs", ["player_id", "stat_group"], unique=False),
        call("idx_player_game_logs_event_date", "player_game_logs", ["event_date"], unique=False),
    ]


def test_drop_helpers_skip_missing_tables(monkeypatch):
    # Given
    operation_proxy = _patch_migration(monkeypatch, FakeInspector())

    # When
    migration._drop_aggregate_table("player_hitting_stats")
    migration._drop_history_table("player_game_logs", ["idx_player_game_logs_event_date"])

    # Then
    operation_proxy.drop_index.assert_not_called()
    operation_proxy.drop_table.assert_not_called()


def test_drop_history_table_only_drops_existing_indexes(monkeypatch):
    # Given
    inspector = FakeInspector(
        tables={"player_game_logs"},
        indexes={
            "player_game_logs": {
                "ix_player_game_logs_id",
                "idx_player_game_logs_player_group",
                "idx_player_game_logs_event_date",
            }
        },
    )
    operation_proxy = _patch_migration(monkeypatch, inspector)

    # When
    migration._drop_history_table("player_game_logs", ["idx_player_game_logs_event_date"])

    # Then
    assert operation_proxy.drop_index.call_args_list == [
        call("idx_player_game_logs_event_date", table_name="player_game_logs"),
        call("idx_player_game_logs_player_group", table_name="player_game_logs"),
        call("ix_player_game_logs_id", table_name="player_game_logs"),
    ]
    operation_proxy.drop_table.assert_called_once_with("player_game_logs")
