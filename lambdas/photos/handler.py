"""Photo API: upload and fetch pet photos in S3, and delete them when FastAPI deletes a pet.

API Gateway calls this for POST /pet/{petId}/uploadImage and GET /pet/{petId}/photos/{file}.
FastAPI invokes it directly with {"action": "delete_pet", "petId": ..., "files": [...]}.
"""

import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError

PHOTOS_BUCKET = os.environ.get("PHOTOS_BUCKET", "petstore-433017611331-g1-photos")
# The function is not in the VPC, so it asks the public API (with the caller's own api_key)
# whether a pet exists, instead of calling the internal load balancer.
API_URL = os.environ.get("API_URL", "https://fu6hh969l7.execute-api.us-east-2.amazonaws.com")

EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}

_s3: Any = None


def _client() -> Any:
    # Created on first use so importing this module (in tests) never touches AWS.
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def _log(**fields: Any) -> None:
    print(json.dumps({"fn": "photos", **fields}))


def _key(pet_id: int, file: str) -> str:
    return f"pets/{pet_id}/{file}"


def _json(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _error(status: int, message: str) -> dict[str, Any]:
    return _json(status, {"code": status, "type": "error", "message": message})


def _safe_file(file: str) -> bool:
    # One plain path segment: nothing that could climb out of pets/{petId}/.
    return bool(file) and "/" not in file and file not in (".", "..")


def _pet_exists(pet_id: int, api_key: str) -> bool:
    request = urllib.request.Request(f"{API_URL}/pet/{pet_id}", headers={"api_key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return bool(response.status == 200)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return False
        raise


def _upload(event: dict[str, Any], pet_id: int) -> dict[str, Any]:
    body = event.get("body") or ""
    data = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()
    if not data:
        return _error(400, "No file uploaded")

    headers = event.get("headers") or {}
    if not _pet_exists(pet_id, headers.get("api_key", "")):
        return _error(404, "Pet not found")

    content_type = headers.get("content-type", "application/octet-stream").split(";")[0]
    file = uuid.uuid4().hex + EXTENSIONS.get(content_type, "")
    _client().put_object(
        Bucket=PHOTOS_BUCKET, Key=_key(pet_id, file), Body=data, ContentType=content_type
    )
    path = f"/pet/{pet_id}/photos/{file}"
    _log(action="upload", petId=pet_id, file=file, bytes=len(data), username=_username(event))
    return _json(200, {"code": 200, "type": "unknown", "message": path})


def _download(pet_id: int, file: str) -> dict[str, Any]:
    if not _safe_file(file):
        return _error(400, "Invalid file name")
    try:
        obj = _client().get_object(Bucket=PHOTOS_BUCKET, Key=_key(pet_id, file))
    except ClientError as err:
        # Without s3:ListBucket, S3 reports a missing key as AccessDenied rather than NoSuchKey.
        if err.response["Error"]["Code"] in ("NoSuchKey", "AccessDenied"):
            return _error(404, "Photo not found")
        raise
    return {
        "statusCode": 200,
        "headers": {"Content-Type": obj.get("ContentType", "application/octet-stream")},
        "body": base64.b64encode(obj["Body"].read()).decode(),
        "isBase64Encoded": True,
    }


def _delete_pet(pet_id: int, files: list[str]) -> dict[str, Any]:
    # The role cannot list the bucket, so FastAPI names the files (from the pet's photoUrls).
    deleted = [f for f in files if _safe_file(f)]
    for file in deleted:
        _client().delete_object(Bucket=PHOTOS_BUCKET, Key=_key(pet_id, file))
    _log(action="delete_pet", petId=pet_id, deleted=len(deleted))
    return {"deleted": len(deleted)}


def _username(event: dict[str, Any]) -> str | None:
    authorizer = event.get("requestContext", {}).get("authorizer") or {}
    name = (authorizer.get("lambda") or {}).get("username")
    return str(name) if name is not None else None


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if event.get("action") == "delete_pet":
        return _delete_pet(int(event["petId"]), list(event.get("files") or []))

    params = event.get("pathParameters") or {}
    try:
        pet_id = int(params.get("petId", ""))
    except ValueError:
        return _error(400, "Invalid ID supplied")

    route = event.get("routeKey", "")
    if route == "POST /pet/{petId}/uploadImage":
        return _upload(event, pet_id)
    if route == "GET /pet/{petId}/photos/{file}":
        return _download(pet_id, params.get("file", ""))
    return _error(404, "Not found")
