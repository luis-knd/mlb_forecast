from interface.rest.main import app


def test_games_get_endpoints_use_typed_200_responses() -> None:
    # Given
    expected_response_schemas = {
        "/api/v1/games": "GameListResponse",
        "/api/v1/games/{game_id}": "GameDetailResponse",
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


def test_game_read_endpoints_document_include_parameter_with_dot_notation_support() -> None:
    # Given
    openapi_schema = app.openapi()
    game_paths = ["/api/v1/games", "/api/v1/games/{game_id}"]

    # When / Then
    for path in game_paths:
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
        assert "home_team" in include_parameter["description"] or "winning_team" in include_parameter["description"]


def test_game_dto_documents_optional_hydrated_team_relations() -> None:
    # Given
    openapi_schema = app.openapi()

    # When
    game_schema = openapi_schema["components"]["schemas"]["GameDTO"]

    # Then
    for field_name in ["home_team", "away_team", "winning_team"]:
        assert game_schema["properties"][field_name]["anyOf"][0] == {"$ref": "#/components/schemas/TeamDTO"}
        assert game_schema["properties"][field_name]["description"].startswith("Hydrated ")
