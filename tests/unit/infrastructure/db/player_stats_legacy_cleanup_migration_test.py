import importlib.util
from pathlib import Path
from unittest.mock import Mock, call


def _load_migration_module():
    module_path = (
        Path(__file__).resolve().parents[4] / "alembic" / "versions" / "3e5c6a4b1d20_drop_legacy_player_stats_table.py"
    )
    spec = importlib.util.spec_from_file_location("player_stats_legacy_cleanup_migration", module_path)
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
    ) -> None:
        self.tables = tables or set()
        self.indexes = indexes or {}

    def get_table_names(self) -> list[str]:
        return sorted(self.tables)

    def get_indexes(self, table_name: str) -> list[dict[str, str]]:
        return [{"name": index_name} for index_name in sorted(self.indexes.get(table_name, set()))]


def _patch_migration(monkeypatch, inspector: FakeInspector) -> Mock:
    operation_proxy = Mock()
    operation_proxy.get_bind.return_value = object()
    monkeypatch.setattr(migration, "op", operation_proxy)
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)
    return operation_proxy


def test_upgrade_drops_legacy_player_stats_table_and_existing_indexes(monkeypatch):
    # Given
    inspector = FakeInspector(
        tables={"player_stats"},
        indexes={
            "player_stats": {
                "ix_player_stats_id",
                "idx_player_stats_team",
                "idx_player_stats_season",
            }
        },
    )
    operation_proxy = _patch_migration(monkeypatch, inspector)

    # When
    migration.upgrade()

    # Then
    assert operation_proxy.drop_index.call_args_list == [
        call("idx_player_stats_season", table_name="player_stats"),
        call("idx_player_stats_team", table_name="player_stats"),
        call("ix_player_stats_id", table_name="player_stats"),
    ]
    operation_proxy.drop_table.assert_called_once_with("player_stats")


def test_upgrade_skips_when_legacy_table_is_already_absent(monkeypatch):
    # Given
    operation_proxy = _patch_migration(monkeypatch, FakeInspector())

    # When
    migration.upgrade()

    # Then
    operation_proxy.drop_index.assert_not_called()
    operation_proxy.drop_table.assert_not_called()


def test_downgrade_recreates_legacy_player_stats_table_and_indexes(monkeypatch):
    # Given
    operation_proxy = _patch_migration(monkeypatch, FakeInspector())

    # When
    migration.downgrade()

    # Then
    operation_proxy.create_table.assert_called_once()
    created_table = operation_proxy.create_table.call_args.args
    assert created_table[0] == "player_stats"
    assert operation_proxy.create_index.call_args_list == [
        call("ix_player_stats_id", "player_stats", ["id"], unique=False),
        call("idx_player_stats_team", "player_stats", ["team_id", "season"], unique=False),
        call("idx_player_stats_season", "player_stats", ["season"], unique=False),
    ]
