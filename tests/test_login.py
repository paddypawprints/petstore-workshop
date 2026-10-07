import hashlib
import time
from typing import Any

import pytest

from lambdas.login import handler as login


class FakeTable:
    def __init__(self, items: dict[str, dict[str, Any]] | None = None) -> None:
        self.items = items or {}
        self.puts: list[dict[str, Any]] = []

    def get_item(self, Key: dict[str, Any]) -> dict[str, Any]:
        item = self.items.get(next(iter(Key.values())))
        return {"Item": item} if item else {}

    def put_item(self, Item: dict[str, Any]) -> None:
        self.puts.append(Item)


@pytest.fixture
def tables(monkeypatch: pytest.MonkeyPatch) -> dict[str, FakeTable]:
    fakes = {
        login.USERS_TABLE: FakeTable(
            {
                "ada": {
                    "username": "ada",
                    "password_sha256": hashlib.sha256(b"lovelace").hexdigest(),
                }
            }
        ),
        login.SESSIONS_TABLE: FakeTable(),
    }
    monkeypatch.setattr(login, "_table", lambda name: fakes[name])
    return fakes


def event(**params: str) -> dict[str, Any]:
    return {"queryStringParameters": params or None}


def test_valid_login_returns_token_and_writes_session(tables: dict[str, FakeTable]) -> None:
    response = login.handler(event(username="ada", password="lovelace"), None)

    assert response["statusCode"] == 200
    token = response["body"]
    assert token
    [session] = tables[login.SESSIONS_TABLE].puts
    assert session["token"] == token
    assert session["username"] == "ada"
    assert 3590 < session["ttl"] - time.time() <= 3600


def test_wrong_password_is_400(tables: dict[str, FakeTable]) -> None:
    response = login.handler(event(username="ada", password="wrong"), None)

    assert response["statusCode"] == 400
    assert tables[login.SESSIONS_TABLE].puts == []


def test_unknown_user_is_400(tables: dict[str, FakeTable]) -> None:
    response = login.handler(event(username="nobody", password="lovelace"), None)

    assert response["statusCode"] == 400


def test_missing_params_is_400(tables: dict[str, FakeTable]) -> None:
    assert login.handler(event(), None)["statusCode"] == 400
    assert login.handler(event(username="ada"), None)["statusCode"] == 400
