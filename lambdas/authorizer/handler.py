"""HTTP API REQUEST authorizer: allow a call only if its api_key is a live session."""

import json
import os
import time
from typing import Any

import boto3

SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "petstore-g1-sessions")

_dynamodb: Any = None


def _table(name: str) -> Any:
    # Created on first use so importing this module (in tests) never touches AWS.
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb.Table(name)


def _log(**fields: Any) -> None:
    # One JSON line per event; never log the token.
    print(json.dumps({"fn": "authorizer", **fields}))


def _deny() -> dict[str, Any]:
    return {"isAuthorized": False}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # HTTP API lowercases header names, so "api_key" is the key whatever the client sent.
    token = (event.get("headers") or {}).get("api_key", "")
    if not token:
        _log(outcome="missing_token")
        return _deny()

    session = _table(SESSIONS_TABLE).get_item(Key={"token": token}).get("Item")
    if not session:
        _log(outcome="unknown_token")
        return _deny()

    # DynamoDB TTL deletes expired items lazily (up to days later), so check ttl ourselves.
    if int(session.get("ttl", 0)) <= time.time():
        _log(outcome="expired", username=session.get("username"))
        return _deny()

    username = str(session["username"])
    _log(outcome="allow", username=username)
    return {"isAuthorized": True, "context": {"username": username}}
