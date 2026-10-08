"""Pets table access. Routes depend on PetStore; tests swap in an in-memory fake."""

from typing import Any

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.dynamo import table
from app.models import Pet

STATUS_INDEX = "status-index"


def _to_item(pet: Pet) -> dict[str, Any]:
    # The table key is petId; the API calls the same field id.
    item = pet.model_dump(exclude_none=True)
    item["petId"] = item.pop("id")
    return item


def _to_pet(item: dict[str, Any]) -> Pet:
    # boto3 returns numbers as Decimal; pydantic turns whole Decimals back into int.
    fields = dict(item)
    fields["id"] = fields.pop("petId")
    return Pet.model_validate(fields)


class PetStore:
    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, pet_id: int) -> Pet | None:
        item = self._table.get_item(Key={"petId": pet_id}).get("Item")
        return _to_pet(item) if item else None

    def put(self, pet: Pet) -> None:
        self._table.put_item(Item=_to_item(pet))

    def replace(self, pet: Pet) -> bool:
        """Overwrite an existing pet. False if there was no pet with that id."""
        try:
            self._table.put_item(
                Item=_to_item(pet), ConditionExpression="attribute_exists(petId)"
            )
        except ClientError as err:
            if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def delete(self, pet_id: int) -> bool:
        """Delete a pet. False if there was nothing to delete."""
        response = self._table.delete_item(Key={"petId": pet_id}, ReturnValues="ALL_OLD")
        return "Attributes" in response

    def by_status(self, status: str) -> list[Pet]:
        # Query the GSI, following LastEvaluatedKey until DynamoDB stops paging.
        kwargs: dict[str, Any] = {
            "IndexName": STATUS_INDEX,
            "KeyConditionExpression": Key("status").eq(status),
        }
        pets: list[Pet] = []
        while True:
            page = self._table.query(**kwargs)
            pets.extend(_to_pet(item) for item in page["Items"])
            if "LastEvaluatedKey" not in page:
                return pets
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def count_by_status(self, status: str) -> int:
        # Select=COUNT returns only how many items matched, not the items themselves.
        kwargs: dict[str, Any] = {
            "IndexName": STATUS_INDEX,
            "KeyConditionExpression": Key("status").eq(status),
            "Select": "COUNT",
        }
        total = 0
        while True:
            page = self._table.query(**kwargs)
            total += int(page["Count"])
            if "LastEvaluatedKey" not in page:
                return total
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def get_pet_store() -> PetStore:
    return PetStore(table(get_settings().pets_table))
