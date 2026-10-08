from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.photos import PhotoCleaner, get_photo_cleaner, photo_files
from app.main import app
from app.models import Pet
from app.stores.pets import get_pet_store
from tests.fakes import FakePetStore, FakePhotoCleaner


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


@pytest.fixture
def photos() -> Iterator[FakePhotoCleaner]:
    fake = FakePhotoCleaner()
    app.dependency_overrides[get_photo_cleaner] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_delete_pet_cleans_up_photos(store: FakePetStore, photos: FakePhotoCleaner) -> None:
    assert client.delete("/pet/1").status_code == 200
    assert client.delete("/pet/1").status_code == 404
    assert [p.id for p in photos.deleted] == [1]


def test_photo_files_keeps_only_this_pets_api_paths() -> None:
    pet = Pet(
        id=7,
        name="x",
        photoUrls=["/pet/7/photos/a.png", "/pet/8/photos/b.png", "data:image/png;base64,AAA"],
    )
    assert photo_files(pet) == ["a.png"]


class RecordingLambda:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def invoke(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def test_cleaner_invokes_lambda_async_only_when_there_are_photos() -> None:
    client_ = RecordingLambda()
    cleaner = PhotoCleaner(client_, "petstore-g1-photos")

    cleaner.delete_pet_photos(Pet(id=7, name="x"))
    cleaner.delete_pet_photos(Pet(id=7, name="x", photoUrls=["/pet/7/photos/a.png"]))

    assert len(client_.calls) == 1
    assert client_.calls[0]["InvocationType"] == "Event"
