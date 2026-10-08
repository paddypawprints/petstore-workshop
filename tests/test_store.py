from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Order, Pet
from app.stores.orders import get_order_store
from app.stores.pets import get_pet_store
from tests.fakes import FakeOrderStore, FakePetStore


@pytest.fixture
def pets() -> Iterator[FakePetStore]:
    fake = FakePetStore()
    fake.put(Pet(id=1, name="Rex", status="available"))
    fake.put(Pet(id=2, name="Tom", status="available"))
    fake.put(Pet(id=3, name="Kit", status="sold"))
    app.dependency_overrides[get_pet_store] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def orders() -> Iterator[FakeOrderStore]:
    fake = FakeOrderStore()
    fake.put(Order(id=5, petId=1, quantity=1, status="placed"))
    app.dependency_overrides[get_order_store] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


client = TestClient(app)


def test_inventory_counts_every_status(pets: FakePetStore) -> None:
    assert client.get("/store/inventory").json() == {"available": 2, "pending": 0, "sold": 1}


def test_place_order(pets: FakePetStore, orders: FakeOrderStore) -> None:
    body = {"petId": 3, "quantity": 2, "shipDate": "2026-10-08T12:00:00Z", "status": "placed"}
    response = client.post("/store/order", json=body)

    assert response.status_code == 200
    order = orders.orders[response.json()["id"]]
    assert order.petId == 3
    assert response.json()["shipDate"] == "2026-10-08T12:00:00Z"


def test_order_for_missing_pet_is_rejected(pets: FakePetStore, orders: FakeOrderStore) -> None:
    assert client.post("/store/order", json={"petId": 99}).status_code == 400
    assert client.post("/store/order", json={"quantity": 1}).status_code == 400


def test_get_order(pets: FakePetStore, orders: FakeOrderStore) -> None:
    assert client.get("/store/order/5").json()["petId"] == 1
    assert client.get("/store/order/99").status_code == 404


def test_delete_order(pets: FakePetStore, orders: FakeOrderStore) -> None:
    assert client.delete("/store/order/5").status_code == 200
    assert client.delete("/store/order/5").status_code == 404
