from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel

from interface.rest.response_handler import APIResponse, CustomJSONEncoder, ResponseHandler, ResponseStatus


class _Payload(BaseModel):
    name: str


def test_custom_json_encoder_handles_common_types():
    # Given
    encoder = CustomJSONEncoder()

    # When / Then
    assert encoder.default(datetime(2026, 1, 1)).startswith("2026-01-01")
    assert encoder.default(date(2026, 1, 1)) == "2026-01-01"
    assert encoder.default(Decimal("1.23")) == 1.23
    assert encoder.default(uuid4())
    assert encoder.default(_Payload(name="x")) == {"name": "x"}


def test_api_response_to_dict_includes_message_and_defaults_errors():
    # Given
    response = APIResponse(status=ResponseStatus.SUCCESS, code=200, data={"x": 1}, message="ok")

    # When
    result = response.to_dict()

    # Then
    assert result["status"] == "success"
    assert result["errors"] == []
    assert result["message"] == "ok"


def test_response_handler_helpers_return_expected_status_codes():
    # Given / When
    success = ResponseHandler.success(data={"a": 1}, message="ok")
    error = ResponseHandler.error(errors="bad", status_code=500)
    not_found = ResponseHandler.not_found("Team", 10)
    bad_request = ResponseHandler.bad_request(errors=["bad"])
    created = ResponseHandler.created(data={"id": 1})
    no_content = ResponseHandler.no_content()

    # Then
    assert success.status_code == 200
    assert error.status_code == 500
    assert not_found.status_code == 404
    assert bad_request.status_code == 400
    assert created.status_code == 201
    assert no_content.status_code == 204
