"""Users table access. The login Lambda reads the same items, so the hash field must match it."""

import hashlib
from typing import Any

from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.dynamo import table
from app.models import User


def hash_password(password: str) -> str:
    # Hex SHA-256 of the password bytes, no salt, no newline: what the login Lambda compares.
    return hashlib.sha256(password.encode()).hexdigest()


def _to_item(user: User, password_sha256: str | None) -> dict[str, Any]:
    item = user.model_dump(exclude_none=True, exclude={"password"})
    if password_sha256 is not None:
        item["password_sha256"] = password_sha256
    return item


def _to_user(item: dict[str, Any]) -> User:
    # The hash never leaves the table.
    fields = {k: v for k, v in item.items() if k != "password_sha256"}
    return User.model_validate(fields)


def _conditional_put(tbl: Any, item: dict[str, Any], condition: str) -> bool:
    try:
        tbl.put_item(Item=item, ConditionExpression=condition)
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise
    return True


class UserStore:
    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, username: str) -> User | None:
        item = self._get_item(username)
        return _to_user(item) if item else None

    def create(self, user: User) -> bool:
        """Add a new user. False if the username is taken (never overwrite an account)."""
        hashed = hash_password(user.password) if user.password else None
        item = _to_item(user, hashed)
        return _conditional_put(self._table, item, "attribute_not_exists(username)")

    def update(self, user: User) -> bool:
        """Replace a user's fields. Keeps the old password unless a new one is given."""
        existing = self._get_item(user.username)
        if existing is None:
            return False
        hashed = hash_password(user.password) if user.password else existing.get("password_sha256")
        return _conditional_put(self._table, _to_item(user, hashed), "attribute_exists(username)")

    def delete(self, username: str) -> bool:
        response = self._table.delete_item(Key={"username": username}, ReturnValues="ALL_OLD")
        return "Attributes" in response

    def _get_item(self, username: str) -> dict[str, Any] | None:
        item: dict[str, Any] | None = self._table.get_item(Key={"username": username}).get("Item")
        return item


def get_user_store() -> UserStore:
    return UserStore(table(get_settings().users_table))
