from src.interface.rest.main import app


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


def test_ingest_players_team_id_parameter_documents_sport_filter_behavior():
    # Given
    openapi_schema = app.openapi()
    ingest_players_parameters = openapi_schema["paths"]["/api/v1/data/ingest/players"]["post"]["parameters"]
    team_id_parameter = next(parameter for parameter in ingest_players_parameters if parameter["name"] == "teamId")

    # Then
    assert "required when source=team_roster" in team_id_parameter["description"]
    assert "optional filter when source=sport_players" in team_id_parameter["description"]
