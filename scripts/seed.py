"""Seed the group tables from the jumpbox: python3 scripts/seed.py

Safe to re-run: an item that already exists is left alone, never overwritten.
"""

import hashlib
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
USERS_TABLE = os.environ.get("USERS_TABLE", "petstore-g1-users")
PETS_TABLE = os.environ.get("PETS_TABLE", "petstore-g1-pets")

USERS = [
    {"username": "ada", "password": "lovelace", "email": "ada@example.com", "userStatus": 1},
]

PETS = [
    {"petId": 1, "name": "Rex", "status": "available", "photoUrls": [], "tags": []},
    {"petId": 2, "name": "Tom", "status": "pending", "photoUrls": [], "tags": []},
    {"petId": 3, "name": "Kit", "status": "sold", "photoUrls": [], "tags": []},
    {
        "petId": 4,
        "name": "Biscuit",
        "status": "available",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": [],
        "tags": [{"id": 1, "name": "friendly"}],
    },
]


def put_new(table: Any, item: dict[str, Any], key: str) -> bool:
    try:
        table.put_item(Item=item, ConditionExpression=f"attribute_not_exists({key})")
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise
    return True


def main() -> None:
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    users, pets = dynamodb.Table(USERS_TABLE), dynamodb.Table(PETS_TABLE)

    for user in USERS:
        item = {k: v for k, v in user.items() if k != "password"}
        # Same format the login Lambda checks: hex SHA-256, no salt, no newline.
        item["password_sha256"] = hashlib.sha256(str(user["password"]).encode()).hexdigest()
        added = put_new(users, item, "username")
        print(f"user {user['username']}: {'added' if added else 'already there'}")

    for pet in PETS:
        added = put_new(pets, pet, "petId")
        print(f"pet {pet['petId']} {pet['name']}: {'added' if added else 'already there'}")


if __name__ == "__main__":
    main()
