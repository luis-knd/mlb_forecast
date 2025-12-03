import pytest
from starlette.status import HTTP_201_CREATED

from src.interface.rest.response_handler import ResponseHandler


@pytest.mark.parametrize(
    "data, message",
    [
        ({"hitting_stats_count": 30, "season": 2025}, "Team hitting statistics ingested successfully for season 2025"),
        (
            {"pitching_stats_count": 28, "season": 2025},
            "Team pitching statistics ingested successfully for season 2025",
        ),
        (
            {"fielding_stats_count": 32, "season": 2025},
            "Team fielding statistics ingested successfully for season 2025",
        ),
        (
            {"catching_stats_count": 26, "season": 2025},
            "Team catching statistics ingested successfully for season 2025",
        ),
    ],
)
def test_created_response_structure_for_team_stats(data, message):
    response = ResponseHandler.created(data=data, message=message)
    assert response.status_code == HTTP_201_CREATED

    # Parse JSON body
    import json

    parsed = json.loads(response.body.decode())

    assert parsed["status"] == "success"
    assert parsed["code"] == HTTP_201_CREATED
    assert isinstance(parsed["errors"], list)
    assert parsed["errors"] == []
    assert parsed["message"] == message

    # Validate core shape
    assert "season" in parsed["data"]
    assert isinstance(parsed["data"]["season"], int)

    # Exactly one of the count keys should be present per case
    count_keys = {
        "hitting_stats_count",
        "pitching_stats_count",
        "fielding_stats_count",
        "catching_stats_count",
    }
    present = count_keys.intersection(parsed["data"].keys())
    assert len(present) == 1
    key = list(present)[0]
    assert isinstance(parsed["data"][key], int)
