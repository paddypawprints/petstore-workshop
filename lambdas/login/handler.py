"""GET /user/login: check a password against Users and open a session in Sessions."""

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import UTC, datetime
from typing import Any

import boto3

USERS_TABLE = os.environ.get("USERS_TABLE", "petstore-g1-users")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "petstore-g1-sessions")
SESSION_SECONDS = 3600

_dynamodb: Any = None


def _table(name: str) -> Any:
    # Created on first use so importing this module (in tests) never touches AWS.
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb.Table(name)


def _log(**fields: Any) -> None:
    # One JSON line per event; never log the password or the token.
    print(json.dumps({"fn": "login", **fields}))


def _invalid() -> dict[str, Any]:
    return {
        "statusCode": 400,
        "headers": {"Content-Type": "text/plain"},
        "body": "Invalid username/password supplied",
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    params = event.get("queryStringParameters") or {}
    username = params.get("username", "")
    password = params.get("password", "")
    if not username or not password:
        _log(outcome="missing_params")
        return _invalid()

    user = _table(USERS_TABLE).get_item(Key={"username": username}).get("Item")
    submitted = hashlib.sha256(password.encode("utf-8")).hexdigest()
    stored = str(user.get("password_sha256", "")) if user else ""
    if not user or not hmac.compare_digest(submitted, stored):
        _log(outcome="bad_credentials", username=username)
        return _invalid()

    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + SESSION_SECONDS
    _table(SESSIONS_TABLE).put_item(Item={"token": token, "username": username, "ttl": expires})
    _log(outcome="ok", username=username, expires=expires)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/plain",
            "X-Expires-After": datetime.fromtimestamp(expires, UTC).isoformat(),
        },
        "body": token,
    }
