from pathlib import Path

import yaml

from interface.rest.main import app


def test_players_get_endpoints_use_typed_200_responses():
    # Given
    expected_response_schemas = {
        "/api/v1/players": "PlayerListResponse",
        "/api/v1/players/{player_id}": "PlayerDetailResponse",
        "/api/v1/players/{player_id}/stats": "PlayerStatsResponse",
    }

    # When
    openapi_schema = app.openapi()

    # Then
    for path, schema_name in expected_response_schemas.items():
        response_schema = openapi_schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        assert response_schema == {"$ref": f"#/components/schemas/{schema_name}"}
        assert schema_name in openapi_schema["components"]["schemas"]


def test_ingest_players_team_id_parameter_documents_internal_team_filter_behavior():
    # Given
    openapi_schema = app.openapi()
    ingest_players_parameters = openapi_schema["paths"]["/api/v1/data/ingest/players"]["post"]["parameters"]
    team_id_parameter = next(parameter for parameter in ingest_players_parameters if parameter["name"] == "teamId")

    # Then
    assert "Internal team ID" in team_id_parameter["description"]
    assert "required when source=team_roster" in team_id_parameter["description"]
    assert "optional filter when source=sport_players" in team_id_parameter["description"]


def test_player_stats_parameter_documents_internal_player_id():
    # Given
    openapi_schema = app.openapi()
    player_stats_parameters = openapi_schema["paths"]["/api/v1/players/{player_id}/stats"]["get"]["parameters"]
    player_id_parameter = next(parameter for parameter in player_stats_parameters if parameter["name"] == "player_id")

    # Then
    assert "Internal player ID" in player_id_parameter["description"]


def test_player_read_endpoints_document_include_parameter_with_dot_notation_support():
    # Given
    openapi_schema = app.openapi()
    player_paths = ["/api/v1/players", "/api/v1/players/{player_id}"]

    # When / Then
    for path in player_paths:
        parameters = openapi_schema["paths"][path]["get"]["parameters"]
        include_parameter = next(parameter for parameter in parameters if parameter["name"] == "include")
        include_schema = (
            include_parameter["schema"]["anyOf"][0]
            if "anyOf" in include_parameter["schema"]
            else include_parameter["schema"]
        )
        assert include_schema["type"] == "array"
        assert include_schema["items"] == {"type": "string"}
        assert "dot notation" in include_parameter["description"]
        assert "current_team" in include_parameter["description"]


def test_player_dto_documents_optional_current_team_relation():
    # Given
    openapi_schema = app.openapi()

    # When
    player_schema = openapi_schema["components"]["schemas"]["PlayerDTO"]

    # Then
    assert player_schema["properties"]["current_team"]["anyOf"][0] == {"$ref": "#/components/schemas/TeamDTO"}
    assert player_schema["properties"]["current_team"]["description"] == "Hydrated current team relation"


def _resolve_openapi_file() -> Path:
    for candidate in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        openapi_path = candidate / "openapi" / "openapi.yml"
        if openapi_path.exists():
            return openapi_path
    raise FileNotFoundError("openapi/openapi.yml not found in any ancestor directory")


def test_openapi_contract_documents_group_all_for_player_stats():
    # Given
    openapi_file = _resolve_openapi_file()
    contract_schema = yaml.safe_load(openapi_file.read_text(encoding="utf-8"))
    player_stats_parameters = contract_schema["paths"]["/api/v1/players/{player_id}/stats"]["get"]["parameters"]
    group_parameter = next(parameter for parameter in player_stats_parameters if parameter["name"] == "group")

    # Then
    assert "all" in group_parameter["schema"]["enum"]


def test_openapi_contract_documents_internal_team_id_for_ingestion():
    # Given
    openapi_file = _resolve_openapi_file()
    contract_schema = yaml.safe_load(openapi_file.read_text(encoding="utf-8"))
    ingest_players_parameters = contract_schema["paths"]["/api/v1/data/ingest/players"]["post"]["parameters"]
    team_id_parameter = next(parameter for parameter in ingest_players_parameters if parameter["name"] == "teamId")

    # Then
    assert "Internal team ID" in team_id_parameter["description"]


def test_player_stats_game_type_parameter_documents_code_meaning():
    # Given
    openapi_schema = app.openapi()
    player_stats_parameters = openapi_schema["paths"]["/api/v1/players/{player_id}/stats"]["get"]["parameters"]
    game_type_parameter = next(parameter for parameter in player_stats_parameters if parameter["name"] == "gameType")

    # Then
    description = game_type_parameter["description"]
    assert "R=Regular Season" in description
    assert "S=Spring Training" in description
    assert "P=Postseason" in description
    assert "W=World Series" in description
    assert "A=All-Star" in description


def test_openapi_contract_documents_player_include_parameter_and_current_team_relation():
    # Given
    openapi_file = _resolve_openapi_file()
    contract_schema = yaml.safe_load(openapi_file.read_text(encoding="utf-8"))

    # When
    player_parameters = contract_schema["paths"]["/api/v1/players"]["get"]["parameters"]
    include_parameter = next(parameter for parameter in player_parameters if parameter["name"] == "include")
    player_schema = contract_schema["components"]["schemas"]["PlayerDTO"]

    # Then
    include_schema = (
        include_parameter["schema"]["anyOf"][0]
        if "anyOf" in include_parameter["schema"]
        else include_parameter["schema"]
    )
    assert include_schema["type"] == "array"
    assert include_schema["items"] == {"type": "string"}
    assert "dot notation" in include_parameter["description"]
    assert player_schema["properties"]["current_team"]["description"] == "Hydrated current team relation"
