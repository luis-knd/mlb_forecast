import importlib.util
from pathlib import Path
from unittest.mock import Mock, call


def _load_migration_module():
    module_path = (
        Path(__file__).resolve().parents[4]
        / "alembic"
        / "versions"
        / "9c18d3f4a7b2_add_history_entry_key_to_player_stats_history.py"
    )
    spec = importlib.util.spec_from_file_location("player_stats_history_entry_key_migration", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration_module()


def test_upgrade_adds_history_entry_key_and_replaces_unique_constraints(monkeypatch):
    # Given
    operation_proxy = Mock()
    monkeypatch.setattr(migration, "op", operation_proxy)

    # When
    migration.upgrade()

    # Then
    assert [call_args.args[0] for call_args in operation_proxy.add_column.call_args_list] == [
        "player_game_logs",
        "player_stat_splits",
    ]
    added_columns = [call_args.args[1] for call_args in operation_proxy.add_column.call_args_list]
    assert [column.name for column in added_columns] == ["history_entry_key", "history_entry_key"]
    assert [column.type.length for column in added_columns] == [255, 255]
    assert [column.nullable for column in added_columns] == [True, True]
    assert [call_args.args for call_args in operation_proxy.alter_column.call_args_list] == [
        ("player_game_logs", "history_entry_key"),
        ("player_stat_splits", "history_entry_key"),
    ]
    altered_types = [call_args.kwargs["existing_type"] for call_args in operation_proxy.alter_column.call_args_list]
    assert [column_type.length for column_type in altered_types] == [255, 255]
    assert [call_args.kwargs["nullable"] for call_args in operation_proxy.alter_column.call_args_list] == [False, False]
    assert operation_proxy.drop_constraint.call_args_list == [
        call("uq_player_game_logs_context", "player_game_logs", type_="unique"),
        call("uq_player_stat_splits_context", "player_stat_splits", type_="unique"),
    ]
    assert operation_proxy.create_unique_constraint.call_args_list == [
        call("uq_player_game_logs_context", "player_game_logs", migration.NEW_HISTORY_CONTEXT_COLUMNS),
        call("uq_player_stat_splits_context", "player_stat_splits", migration.NEW_HISTORY_CONTEXT_COLUMNS),
    ]
    assert operation_proxy.execute.call_count == 2


def test_downgrade_restores_external_reference_uniqueness(monkeypatch):
    # Given
    operation_proxy = Mock()
    monkeypatch.setattr(migration, "op", operation_proxy)

    # When
    migration.downgrade()

    # Then
    assert operation_proxy.drop_constraint.call_args_list == [
        call("uq_player_game_logs_context", "player_game_logs", type_="unique"),
        call("uq_player_stat_splits_context", "player_stat_splits", type_="unique"),
    ]
    assert operation_proxy.create_unique_constraint.call_args_list == [
        call("uq_player_game_logs_context", "player_game_logs", migration.OLD_HISTORY_CONTEXT_COLUMNS),
        call("uq_player_stat_splits_context", "player_stat_splits", migration.OLD_HISTORY_CONTEXT_COLUMNS),
    ]
    assert operation_proxy.drop_column.call_args_list == [
        call("player_game_logs", "history_entry_key"),
        call("player_stat_splits", "history_entry_key"),
    ]
