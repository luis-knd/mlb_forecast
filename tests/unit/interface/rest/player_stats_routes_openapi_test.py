from pathlib import Path

import yaml

from interface.rest.main import app


def _resolve_openapi_file() -> Path:
    for candidate in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        openapi_path = candidate / "openapi" / "openapi.yml"
        if openapi_path.exists():
            return openapi_path
    raise FileNotFoundError("openapi/openapi.yml not found in any ancestor directory")


def test_persisted_player_stats_endpoints_use_typed_200_responses():
    # Given
    expected_response_schemas = {
        "/api/v1/players/{player_id}/stats/season": "PlayerStatsAggregateResponse",
        "/api/v1/players/{player_id}/stats/career": "PlayerStatsAggregateResponse",
        "/api/v1/players/{player_id}/stats/year-by-year": "PlayerStatsAggregateResponse",
        "/api/v1/players/{player_id}/stats/game-log": "PlayerStatsHistoryResponse",
        "/api/v1/players/{player_id}/stats/splits": "PlayerStatsHistoryResponse",
    }

    # When
    openapi_schema = app.openapi()

    # Then
    for path, schema_name in expected_response_schemas.items():
        response_schema = openapi_schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        assert response_schema == {"$ref": f"#/components/schemas/{schema_name}"}


def test_persisted_player_stats_ingestion_endpoints_use_typed_201_responses():
    # Given
    expected_paths = [
        "/api/v1/data/ingest/player_stats/season",
        "/api/v1/data/ingest/player_stats/history",
    ]

    # When
    openapi_schema = app.openapi()

    # Then
    for path in expected_paths:
        response_schema = openapi_schema["paths"][path]["post"]["responses"]["201"]["content"]["application/json"][
            "schema"
        ]
        assert response_schema == {"$ref": "#/components/schemas/PlayerStatsIngestionResponse"}


def test_openapi_contract_documents_persisted_player_stats_paths():
    # Given
    contract_schema = yaml.safe_load(_resolve_openapi_file().read_text(encoding="utf-8"))

    # When / Then
    assert "/api/v1/players/{player_id}/stats/season" in contract_schema["paths"]
    assert "/api/v1/players/{player_id}/stats/game-log" in contract_schema["paths"]
    assert "/api/v1/data/ingest/player_stats/season" in contract_schema["paths"]
    assert "PlayerStatsAggregateResponse" in contract_schema["components"]["schemas"]
    assert "PlayerStatsHistoryResponse" in contract_schema["components"]["schemas"]
    assert "PlayerStatsIngestionResponse" in contract_schema["components"]["schemas"]


def test_openapi_contract_documents_limit_and_days_back_for_persisted_history():
    # Given
    openapi_schema = app.openapi()
    game_log_parameters = openapi_schema["paths"]["/api/v1/players/{player_id}/stats/game-log"]["get"]["parameters"]

    # When
    days_back_parameter = next(parameter for parameter in game_log_parameters if parameter["name"] == "daysBack")
    limit_parameter = next(parameter for parameter in game_log_parameters if parameter["name"] == "limit")

    # Then
    assert "rolling window" in days_back_parameter["description"]
    assert limit_parameter["schema"]["anyOf"][0]["type"] == "integer"


def test_persisted_player_stats_read_endpoints_are_not_classified_as_data_ingestion():
    # Given
    read_paths = [
        "/api/v1/players/{player_id}/stats/season",
        "/api/v1/players/{player_id}/stats/career",
        "/api/v1/players/{player_id}/stats/year-by-year",
        "/api/v1/players/{player_id}/stats/game-log",
        "/api/v1/players/{player_id}/stats/splits",
    ]

    # When
    openapi_schema = app.openapi()

    # Then
    for path in read_paths:
        operation_tags = openapi_schema["paths"][path]["get"]["tags"]
        assert operation_tags == ["Players", "Stats"]


def test_openapi_tag_metadata_is_defined_for_live_schema_and_static_contract():
    # Given
    expected_tag_descriptions = {
        "Teams": "Team catalogue, lookup endpoints and team-focused operations.",
        "Games": "Game schedule, retrieval and game-related ingestion workflows.",
        "Players": "Player lookup, hydration and player-focused operations.",
        "Stats": "Read-only statistical views served from persisted data.",
        "Predictions": "Prediction generation and prediction retrieval endpoints.",
        "Data Ingestion": "Write-oriented endpoints that ingest or refresh external MLB data.",
        "System": "Operational endpoints for health, cache and runtime diagnostics.",
        "ML Model": "Machine learning maintenance operations such as retraining.",
    }

    # When
    live_openapi_schema = app.openapi()
    contract_schema = yaml.safe_load(_resolve_openapi_file().read_text(encoding="utf-8"))
    live_tags = {tag["name"]: tag["description"] for tag in live_openapi_schema["tags"]}
    contract_tags = {tag["name"]: tag["description"] for tag in contract_schema["tags"]}

    # Then
    assert live_tags == expected_tag_descriptions
    assert contract_tags == expected_tag_descriptions


def test_live_openapi_operations_do_not_repeat_tags():
    # Given
    openapi_schema = app.openapi()
    duplicated_operation_tags: dict[tuple[str, str], list[str]] = {}
    allowed_methods = {"get", "post", "put", "patch", "delete"}

    # When
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if method not in allowed_methods:
                continue

            operation_tags = operation.get("tags", [])
            normalized_tags = list(dict.fromkeys(operation_tags))
            if operation_tags != normalized_tags:
                duplicated_operation_tags[(path, method)] = operation_tags

    # Then
    assert not duplicated_operation_tags
