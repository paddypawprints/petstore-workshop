"""Request and response shapes from openapi/petstore.yaml (camelCase names match the spec)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PetStatus = Literal["available", "pending", "sold"]
PET_STATUSES: tuple[str, ...] = ("available", "pending", "sold")


class Category(BaseModel):
    id: int | None = None
    name: str | None = None


class Tag(BaseModel):
    id: int | None = None
    name: str | None = None


class Pet(BaseModel):
    id: int | None = None
    name: str
    category: Category | None = None
    photoUrls: list[str] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    status: PetStatus | None = None


class User(BaseModel):
    id: int | None = None
    username: str
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    password: str | None = None
    phone: str | None = None
    userStatus: int | None = None


OrderStatus = Literal["placed", "approved", "delivered"]


class Order(BaseModel):
    id: int | None = None
    petId: int | None = None
    quantity: int | None = None
    shipDate: datetime | None = None
    status: OrderStatus | None = None
    complete: bool | None = None
