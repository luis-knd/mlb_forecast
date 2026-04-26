from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from interface.rest.exception_handlers import ExceptionHandlerMiddleware, domain_exception_handler
from interface.rest.exception_handlers import DomainExceptions


class _Model(BaseModel):
    age: int


@pytest.mark.asyncio
async def test_http_and_validation_exception_handlers(monkeypatch):
    # Given
    monkeypatch.setattr(
        "interface.rest.exception_handlers.ResponseHandler.error",
        lambda **kwargs: {"type": "error", **kwargs},
    )
    monkeypatch.setattr(
        "interface.rest.exception_handlers.ResponseHandler.bad_request",
        lambda **kwargs: {"type": "bad_request", **kwargs},
    )

    http_exc = HTTPException(status_code=404, detail="nope")

    try:
        _Model(age="invalid")
    except ValidationError as validation_exc:
        val_resp = await ExceptionHandlerMiddleware.validation_exception_handler(SimpleNamespace(), validation_exc)

    non_val_resp = await ExceptionHandlerMiddleware.validation_exception_handler(SimpleNamespace(), RuntimeError("x"))
    http_resp = await ExceptionHandlerMiddleware.http_exception_handler(SimpleNamespace(), http_exc)

    # Then
    assert http_resp["status_code"] == 404
    assert non_val_resp["status_code"] == 400
    assert val_resp["type"] == "bad_request"


@pytest.mark.asyncio
async def test_sqlalchemy_and_general_exception_handlers(monkeypatch):
    # Given
    monkeypatch.setattr(
        "interface.rest.exception_handlers.ResponseHandler.error",
        lambda **kwargs: {"type": "error", **kwargs},
    )
    monkeypatch.setattr(
        "interface.rest.exception_handlers.ResponseHandler.bad_request",
        lambda **kwargs: {"type": "bad_request", **kwargs},
    )

    # When
    generic_db = await ExceptionHandlerMiddleware.sqlalchemy_exception_handler(SimpleNamespace(), SQLAlchemyError("db"))
    integrity = await ExceptionHandlerMiddleware.sqlalchemy_exception_handler(
        SimpleNamespace(), IntegrityError("stmt", "params", Exception("orig"))
    )
    non_db = await ExceptionHandlerMiddleware.sqlalchemy_exception_handler(SimpleNamespace(), RuntimeError("x"))
    general = await ExceptionHandlerMiddleware.general_exception_handler(SimpleNamespace(), RuntimeError("boom"))

    # Then
    assert generic_db["status_code"] == 500
    assert integrity["type"] == "bad_request"
    assert non_db["status_code"] == 500
    assert general["status_code"] == 500


@pytest.mark.asyncio
async def test_domain_exception_handler_routes_each_exception(monkeypatch):
    # Given
    monkeypatch.setattr(
        "interface.rest.exception_handlers.ResponseHandler.not_found", lambda *args, **kwargs: {"nf": args}
    )
    monkeypatch.setattr(
        "interface.rest.exception_handlers.ResponseHandler.bad_request", lambda **kwargs: {"br": kwargs}
    )
    monkeypatch.setattr("interface.rest.exception_handlers.ResponseHandler.error", lambda **kwargs: {"err": kwargs})

    # When
    team = await domain_exception_handler(SimpleNamespace(), DomainExceptions.TeamNotFoundError(1))
    player = await domain_exception_handler(SimpleNamespace(), DomainExceptions.PlayerNotFoundError(2))
    game = await domain_exception_handler(SimpleNamespace(), DomainExceptions.GameNotFoundError(3))
    invalid = await domain_exception_handler(SimpleNamespace(), DomainExceptions.InvalidDataError("bad"))
    external = await domain_exception_handler(SimpleNamespace(), DomainExceptions.ExternalServiceError("svc", "down"))
    unknown = await domain_exception_handler(SimpleNamespace(), RuntimeError("unknown"))

    # Then
    assert team["nf"][0] == "Team"
    assert player["nf"][0] == "Player"
    assert game["nf"][0] == "Game"
    assert "br" in invalid
    assert external["err"]["status_code"] == 503
    assert unknown["err"]["status_code"] == 500
