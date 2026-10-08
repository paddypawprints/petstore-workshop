from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Pet
from app.stores.pets import get_pet_store
from tests.fakes import FakePetStore


@pytest.fixture
def store() -> Iterator[FakePetStore]:
    fake = FakePetStore()
    fake.put(Pet(id=1, name="Rex", status="available"))
    fake.put(Pet(id=2, name="Tom", status="pending"))
    fake.put(Pet(id=3, name="Kit", status="sold"))
    app.dependency_overrides[get_pet_store] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


client = TestClient(app)


def test_get_pet(store: FakePetStore) -> None:
    response = client.get("/pet/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Rex",
        "photoUrls": [],
        "tags": [],
        "status": "available",
    }


def test_get_missing_pet_is_404(store: FakePetStore) -> None:
    assert client.get("/pet/99").status_code == 404


def test_add_pet_without_id_gets_one(store: FakePetStore) -> None:
    response = client.post("/pet", json={"name": "New", "photoUrls": []})

    assert response.status_code == 200
    pet_id = response.json()["id"]
    assert store.pets[pet_id].name == "New"


def test_update_pet_replaces_it(store: FakePetStore) -> None:
    body = {"id": 1, "name": "Rex", "photoUrls": ["/pet/1/photos/a.png"], "status": "sold"}

    assert client.put("/pet", json=body).status_code == 200
    assert store.pets[1].photoUrls == ["/pet/1/photos/a.png"]


def test_update_pet_errors(store: FakePetStore) -> None:
    assert client.put("/pet", json={"name": "x", "photoUrls": []}).status_code == 400
    assert client.put("/pet", json={"id": 99, "name": "x", "photoUrls": []}).status_code == 404


def test_find_by_status_accepts_repeated_and_comma_separated(store: FakePetStore) -> None:
    repeated = client.get("/pet/findByStatus?status=available&status=sold").json()
    commas = client.get("/pet/findByStatus?status=available,sold").json()

    assert sorted(p["id"] for p in repeated) == [1, 3]
    assert sorted(p["id"] for p in commas) == [1, 3]


def test_find_by_status_defaults_to_available(store: FakePetStore) -> None:
    assert [p["id"] for p in client.get("/pet/findByStatus").json()] == [1]


def test_find_by_status_rejects_unknown_status(store: FakePetStore) -> None:
    assert client.get("/pet/findByStatus?status=lost").status_code == 400


def test_update_with_form(store: FakePetStore) -> None:
    response = client.post("/pet/2?status=sold")

    assert response.status_code == 200
    assert store.pets[2].status == "sold"
    assert store.pets[2].name == "Tom"
    assert client.post("/pet/2?status=lost").status_code == 400


def test_delete_pet(store: FakePetStore) -> None:
    assert client.delete("/pet/1").status_code == 200
    assert client.delete("/pet/1").status_code == 404
