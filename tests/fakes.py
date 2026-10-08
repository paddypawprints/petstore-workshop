"""In-memory stand-ins for the DynamoDB stores, swapped in with app.dependency_overrides."""

from app.core.photos import PhotoCleaner
from app.models import Order, Pet, User
from app.stores.orders import OrderStore
from app.stores.pets import PetStore
from app.stores.users import UserStore, hash_password


class FakePetStore(PetStore):
    def __init__(self) -> None:
        self.pets: dict[int, Pet] = {}

    def get(self, pet_id: int) -> Pet | None:
        return self.pets.get(pet_id)

    def put(self, pet: Pet) -> None:
        assert pet.id is not None
        self.pets[pet.id] = pet

    def replace(self, pet: Pet) -> bool:
        if pet.id not in self.pets:
            return False
        self.put(pet)
        return True

    def delete(self, pet_id: int) -> Pet | None:
        return self.pets.pop(pet_id, None)

    def by_status(self, status: str) -> list[Pet]:
        return [p for p in self.pets.values() if p.status == status]

    def count_by_status(self, status: str) -> int:
        return len(self.by_status(status))


class FakeOrderStore(OrderStore):
    def __init__(self) -> None:
        self.orders: dict[int, Order] = {}

    def get(self, order_id: int) -> Order | None:
        return self.orders.get(order_id)

    def put(self, order: Order) -> None:
        assert order.id is not None
        self.orders[order.id] = order

    def delete(self, order_id: int) -> bool:
        return self.orders.pop(order_id, None) is not None


class FakeUserStore(UserStore):
    def __init__(self) -> None:
        # username -> (user without password, password hash)
        self.users: dict[str, tuple[User, str | None]] = {}

    def get(self, username: str) -> User | None:
        entry = self.users.get(username)
        return entry[0] if entry else None

    def create(self, user: User) -> bool:
        if user.username in self.users:
            return False
        hashed = hash_password(user.password) if user.password else None
        self.users[user.username] = (user.model_copy(update={"password": None}), hashed)
        return True

    def update(self, user: User) -> bool:
        entry = self.users.get(user.username)
        if entry is None:
            return False
        hashed = hash_password(user.password) if user.password else entry[1]
        self.users[user.username] = (user.model_copy(update={"password": None}), hashed)
        return True

    def delete(self, username: str) -> bool:
        return self.users.pop(username, None) is not None


class FakePhotoCleaner(PhotoCleaner):
    def __init__(self) -> None:
        self.deleted: list[Pet] = []

    def delete_pet_photos(self, pet: Pet) -> None:
        self.deleted.append(pet)
