from contextlib import suppress
from unittest.mock import MagicMock

from infrastructure.db import database


def test_get_db_closes_session(monkeypatch):
    # Given
    fake_session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", MagicMock(return_value=fake_session))

    # When
    generator = database.get_db()
    yielded = next(generator)
    with suppress(StopIteration):
        next(generator)

    # Then
    assert yielded is fake_session
    fake_session.close.assert_called_once()


def test_db_session_commits_and_rollbacks(monkeypatch):
    # Given
    fake_session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", MagicMock(return_value=fake_session))

    # When
    with database.db_session() as session:
        assert session is fake_session

    # Then
    fake_session.commit.assert_called_once()
    fake_session.close.assert_called_once()

    # Given error branch
    fake_session_error = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", MagicMock(return_value=fake_session_error))

    # When / Then
    try:
        with database.db_session():
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    fake_session_error.rollback.assert_called_once()
    fake_session_error.close.assert_called_once()


def test_create_and_drop_tables(monkeypatch):
    # Given
    create_all = MagicMock()
    drop_all = MagicMock()
    metadata = MagicMock(create_all=create_all, drop_all=drop_all)
    monkeypatch.setattr(database, "Base", MagicMock(metadata=metadata))

    # When
    database.create_tables()
    database.drop_tables()

    # Then
    create_all.assert_called_once_with(bind=database.engine)
    drop_all.assert_called_once_with(bind=database.engine)
