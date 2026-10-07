import time
from decimal import Decimal
from typing import Any

import pytest

from lambdas.authorizer import handler as authorizer


class FakeTable:
    def __init__(self, items: dict[str, dict[str, Any]]) -> None:
        self.items = items

    def get_item(self, Key: dict[str, Any]) -> dict[str, Any]:
        item = self.items.get(next(iter(Key.values())))
        return {"Item": item} if item else {}


@pytest.fixture(autouse=True)
def sessions(monkeypatch: pytest.MonkeyPatch) -> FakeTable:
    now = int(time.time())
    # boto3's resource API returns DynamoDB numbers as Decimal, so the fake does too.
    fake = FakeTable(
        {
            "live": {"token": "live", "username": "ada", "ttl": Decimal(now + 600)},
            "stale": {"token": "stale", "username": "ada", "ttl": Decimal(now - 1)},
        }
    )
    monkeypatch.setattr(authorizer, "_table", lambda name: fake)
    return fake


def event(headers: dict[str, str] | None) -> dict[str, Any]:
    return {"headers": headers}


def test_live_session_is_allowed_with_username() -> None:
    response = authorizer.handler(event({"api_key": "live"}), None)

    assert response == {"isAuthorized": True, "context": {"username": "ada"}}


def test_expired_session_is_denied() -> None:
    assert authorizer.handler(event({"api_key": "stale"}), None) == {"isAuthorized": False}


def test_unknown_token_is_denied() -> None:
    assert authorizer.handler(event({"api_key": "nope"}), None) == {"isAuthorized": False}


def test_missing_header_is_denied() -> None:
    assert authorizer.handler(event({}), None) == {"isAuthorized": False}
    assert authorizer.handler(event(None), None) == {"isAuthorized": False}
