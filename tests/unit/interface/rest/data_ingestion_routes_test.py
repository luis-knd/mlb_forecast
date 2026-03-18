from unittest.mock import MagicMock

from interface.rest.data_ingestion_routes import get_data_ingestion_use_cases


def test_get_data_ingestion_use_cases_success():
    """
    Verify get_data_ingestion_use_cases initializes correctly.
    """
    mock_db = MagicMock()

    # Should not raise any error now
    use_cases = get_data_ingestion_use_cases(db=mock_db)

    assert "ingest_teams" in use_cases
    assert use_cases["ingest_teams"] is not None
