from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.ids import new_id
from app.models import PET_STATUSES, Order
from app.stores.orders import OrderStore, get_order_store
from app.stores.pets import PetStore, get_pet_store

router = APIRouter(prefix="/store", tags=["store"])

Orders = Annotated[OrderStore, Depends(get_order_store)]
Pets = Annotated[PetStore, Depends(get_pet_store)]


@router.get("/inventory")
def get_inventory(pets: Pets) -> dict[str, int]:
    # Computed, not stored: count pets per status through the status index.
    return {status: pets.count_by_status(status) for status in PET_STATUSES}


@router.post("/order", response_model_exclude_none=True)
def place_order(order: Order, orders: Orders, pets: Pets) -> Order:
    if order.petId is None or pets.get(order.petId) is None:
        raise HTTPException(status_code=400, detail="Invalid input")
    if order.id is None:
        order = order.model_copy(update={"id": new_id()})
    orders.put(order)
    return order


@router.get("/order/{orderId}", response_model_exclude_none=True)
def get_order_by_id(orderId: int, orders: Orders) -> Order:
    order = orders.get(orderId)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/order/{orderId}")
def delete_order(orderId: int, orders: Orders) -> dict[str, str]:
    if not orders.delete(orderId):
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted"}
