from src.interface.rest.main import app


def test_all_json_responses_have_structured_schema():
    # Given
    openapi_schema = app.openapi()
    invalid_responses = []
    allowed_methods = {"get", "post", "put", "patch", "delete", "options", "head"}

    # When
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in allowed_methods:
                continue

            responses = operation.get("responses", {})
            for status_code, response in responses.items():
                content = (response or {}).get("content", {})
                json_media = content.get("application/json")
                if not json_media:
                    continue

                schema = (json_media or {}).get("schema")
                if schema is None:
                    invalid_responses.append((path, method, status_code, "missing_schema"))
                    continue
                if schema == {}:
                    invalid_responses.append((path, method, status_code, "empty_schema"))
                    continue
                if isinstance(schema, dict) and schema.get("type") == "string":
                    invalid_responses.append((path, method, status_code, "string_schema"))

    # Then
    assert not invalid_responses, f"Invalid OpenAPI JSON schemas detected: {invalid_responses}"
