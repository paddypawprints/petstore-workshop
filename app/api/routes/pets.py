from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.ids import new_id
from app.core.photos import PhotoCleaner, get_photo_cleaner
from app.models import PET_STATUSES, Pet
from app.stores.pets import PetStore, get_pet_store

router = APIRouter(prefix="/pet", tags=["pet"])

Store = Annotated[PetStore, Depends(get_pet_store)]
Photos = Annotated[PhotoCleaner, Depends(get_photo_cleaner)]


@router.post("", response_model_exclude_none=True)
def add_pet(pet: Pet, store: Store) -> Pet:
    if pet.id is None:
        pet = pet.model_copy(update={"id": new_id()})
    store.put(pet)
    return pet


@router.put("", response_model_exclude_none=True)
def update_pet(pet: Pet, store: Store) -> Pet:
    if pet.id is None:
        raise HTTPException(status_code=400, detail="Invalid ID supplied")
    if not store.replace(pet):
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


# Declared before /{petId}: routes match in order, and "findByStatus" would otherwise
# be parsed as a petId and fail integer validation.
@router.get("/findByStatus", response_model_exclude_none=True)
def find_pets_by_status(
    store: Store, status: Annotated[list[str] | None, Query()] = None
) -> list[Pet]:
    # Accept both ?status=a&status=b and ?status=a,b.
    wanted = [s for value in status or ["available"] for s in value.split(",") if s]
    if any(s not in PET_STATUSES for s in wanted):
        raise HTTPException(status_code=400, detail="Invalid status value")
    return [pet for s in dict.fromkeys(wanted) for pet in store.by_status(s)]


@router.get("/{petId}", response_model_exclude_none=True)
def get_pet_by_id(petId: int, store: Store) -> Pet:
    pet = store.get(petId)
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


@router.post("/{petId}", response_model_exclude_none=True)
def update_pet_with_form(
    petId: int, store: Store, name: str | None = None, status: str | None = None
) -> Pet:
    if status is not None and status not in PET_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid input")
    pet = store.get(petId)
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    changes = {k: v for k, v in {"name": name, "status": status}.items() if v is not None}
    pet = pet.model_copy(update=changes)
    store.put(pet)
    return pet


@router.delete("/{petId}")
def delete_pet(petId: int, store: Store, photos: Photos) -> dict[str, str]:
    pet = store.delete(petId)
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    photos.delete_pet_photos(pet)
    return {"message": "Pet deleted"}
