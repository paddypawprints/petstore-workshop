"""FastAPI never touches S3; it asks the photo Lambda to delete a pet's photos."""

import json
import logging
from typing import Any

import boto3

from app.core.config import get_settings
from app.models import Pet

log = logging.getLogger(__name__)


def photo_files(pet: Pet) -> list[str]:
    # photoUrls holds API paths like /pet/7/photos/abc.png; keep only this pet's file names.
    prefix = f"/pet/{pet.id}/photos/"
    return [url[len(prefix) :] for url in pet.photoUrls if url.startswith(prefix)]


class PhotoCleaner:
    def __init__(self, client: Any, function_name: str) -> None:
        self._client = client
        self._function = function_name

    def delete_pet_photos(self, pet: Pet) -> None:
        files = photo_files(pet)
        if not files:
            return
        payload = {"action": "delete_pet", "petId": pet.id, "files": files}
        try:
            # "Event" is fire-and-forget: the delete request doesn't wait on S3.
            self._client.invoke(
                FunctionName=self._function,
                InvocationType="Event",
                Payload=json.dumps(payload).encode(),
            )
        except Exception:
            # The pet is already gone; leftover photos are not worth failing the request.
            log.exception("photo cleanup failed for pet %s", pet.id)


_lambda: Any = None


def get_photo_cleaner() -> PhotoCleaner:
    global _lambda
    settings = get_settings()
    if _lambda is None:
        _lambda = boto3.client("lambda", region_name=settings.aws_default_region)
    return PhotoCleaner(_lambda, settings.photos_function)
