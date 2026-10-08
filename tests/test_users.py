from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from app.stores.users import get_user_store, hash_password
from tests.fakes import FakeUserStore


@pytest.fixture
def users() -> Iterator[FakeUserStore]:
    fake = FakeUserStore()
    fake.create(User(username="ada", email="ada@example.com", password="lovelace"))
    fake.create(User(username="bob", password="builder"))
    app.dependency_overrides[get_user_store] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


client = TestClient(app)
AS_ADA = {"x-username": "ada"}


def test_create_user_hashes_password_and_never_returns_it(users: FakeUserStore) -> None:
    response = client.post("/user", json={"username": "cy", "password": "secret"})

    assert response.status_code == 200
    assert "password" not in response.json()
    assert users.users["cy"][1] == hash_password("secret")


def test_create_user_cannot_overwrite_existing(users: FakeUserStore) -> None:
    response = client.post("/user", json={"username": "ada", "password": "hijack"})

    assert response.status_code == 400
    assert users.users["ada"][1] == hash_password("lovelace")


def test_create_with_list_is_all_or_nothing(users: FakeUserStore) -> None:
    ok = client.post("/user/createWithList", json=[{"username": "c1"}, {"username": "c2"}])
    clash = client.post("/user/createWithList", json=[{"username": "c3"}, {"username": "bob"}])

    assert ok.status_code == 200
    assert clash.status_code == 400
    assert "c3" not in users.users


def test_get_user_hides_password(users: FakeUserStore) -> None:
    body = client.get("/user/ada").json()

    assert body == {"username": "ada", "email": "ada@example.com"}
    assert client.get("/user/nobody").status_code == 404


def test_update_own_user_keeps_password_unless_given(users: FakeUserStore) -> None:
    response = client.put("/user/ada", json={"username": "ada", "phone": "555"}, headers=AS_ADA)

    assert response.status_code == 200
    assert users.users["ada"][0].phone == "555"
    assert users.users["ada"][1] == hash_password("lovelace")


def test_update_or_delete_someone_else_is_forbidden(users: FakeUserStore) -> None:
    assert client.put("/user/bob", json={"username": "bob"}, headers=AS_ADA).status_code == 403
    assert client.delete("/user/bob", headers=AS_ADA).status_code == 403
    assert client.delete("/user/ada").status_code == 403
    assert "bob" in users.users


def test_delete_own_user(users: FakeUserStore) -> None:
    assert client.delete("/user/ada", headers=AS_ADA).status_code == 200
    assert "ada" not in users.users
