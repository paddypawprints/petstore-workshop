import base64
import json
from typing import Any

import pytest
from botocore.exceptions import ClientError

from lambdas.photos import handler as photos


class FakeBody:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def read(self) -> bytes:
        return self.data


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        self.objects[Key] = (Body, ContentType)

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            # What S3 really returns for a missing key when the role can't ListBucket.
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
        data, content_type = self.objects[Key]
        return {"Body": FakeBody(data), "ContentType": content_type}

    def delete_object(self, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)


@pytest.fixture
def s3(monkeypatch: pytest.MonkeyPatch) -> FakeS3:
    fake = FakeS3()
    monkeypatch.setattr(photos, "_client", lambda: fake)
    monkeypatch.setattr(photos, "_pet_exists", lambda pet_id, api_key: pet_id == 1)
    return fake


def upload(pet_id: str, data: bytes) -> dict[str, Any]:
    return {
        "routeKey": "POST /pet/{petId}/uploadImage",
        "pathParameters": {"petId": pet_id},
        "headers": {"content-type": "image/png", "api_key": "tok"},
        "body": base64.b64encode(data).decode(),
        "isBase64Encoded": True,
    }


def download(pet_id: str, file: str) -> dict[str, Any]:
    return {
        "routeKey": "GET /pet/{petId}/photos/{file}",
        "pathParameters": {"petId": pet_id, "file": file},
    }


def test_upload_then_download_round_trip(s3: FakeS3) -> None:
    response = photos.handler(upload("1", b"\x89PNG"), None)

    assert response["statusCode"] == 200
    path = json.loads(response["body"])["message"]
    assert path.startswith("/pet/1/photos/") and path.endswith(".png")

    file = path.rsplit("/", 1)[1]
    assert f"pets/1/{file}" in s3.objects
    got = photos.handler(download("1", file), None)
    assert got["isBase64Encoded"] is True
    assert base64.b64decode(got["body"]) == b"\x89PNG"
    assert got["headers"]["Content-Type"] == "image/png"


def test_upload_for_missing_pet_stores_nothing(s3: FakeS3) -> None:
    assert photos.handler(upload("2", b"x"), None)["statusCode"] == 404
    assert s3.objects == {}


def test_upload_rejects_empty_body_and_bad_id(s3: FakeS3) -> None:
    assert photos.handler(upload("1", b""), None)["statusCode"] == 400
    assert photos.handler(upload("abc", b"x"), None)["statusCode"] == 400


def test_download_missing_or_unsafe_file(s3: FakeS3) -> None:
    assert photos.handler(download("1", "nope.png"), None)["statusCode"] == 404
    assert photos.handler(download("1", ".."), None)["statusCode"] == 400


def test_delete_pet_removes_named_files(s3: FakeS3) -> None:
    s3.objects["pets/1/a.png"] = (b"a", "image/png")
    s3.objects["pets/1/b.png"] = (b"b", "image/png")

    result = photos.handler({"action": "delete_pet", "petId": 1, "files": ["a.png", "../x"]}, None)

    assert result == {"deleted": 1}
    assert list(s3.objects) == ["pets/1/b.png"]
