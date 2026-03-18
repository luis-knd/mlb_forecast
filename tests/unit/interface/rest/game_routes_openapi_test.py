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
