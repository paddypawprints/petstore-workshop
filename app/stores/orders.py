"""Orders table access. Routes depend on OrderStore; tests swap in an in-memory fake."""

from typing import Any

from app.core.config import get_settings
from app.core.dynamo import table
from app.models import Order


def _to_item(order: Order) -> dict[str, Any]:
    # mode="json" turns shipDate into an ISO string; DynamoDB has no datetime type.
    item = order.model_dump(mode="json", exclude_none=True)
    item["orderId"] = item.pop("id")
    return item


def _to_order(item: dict[str, Any]) -> Order:
    fields = dict(item)
    fields["id"] = fields.pop("orderId")
    return Order.model_validate(fields)


class OrderStore:
    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, order_id: int) -> Order | None:
        item = self._table.get_item(Key={"orderId": order_id}).get("Item")
        return _to_order(item) if item else None

    def put(self, order: Order) -> None:
        self._table.put_item(Item=_to_item(order))

    def delete(self, order_id: int) -> bool:
        """Delete an order. False if there was nothing to delete."""
        response = self._table.delete_item(Key={"orderId": order_id}, ReturnValues="ALL_OLD")
        return "Attributes" in response


def get_order_store() -> OrderStore:
    return OrderStore(table(get_settings().orders_table))
