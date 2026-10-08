from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.models import User
from app.stores.users import UserStore, get_user_store

router = APIRouter(prefix="/user", tags=["user"])

Users = Annotated[UserStore, Depends(get_user_store)]
# Set by API Gateway from the authorizer's context; it overwrites anything the client sent.
CallerName = Annotated[str | None, Header(alias="x-username")]


def _require_self(caller: str | None, username: str) -> None:
    if not caller or caller != username:
        raise HTTPException(status_code=403, detail="You can only change your own user")


@router.post("", response_model_exclude_none=True, response_model_exclude={"password"})
def create_user(user: User, users: Users) -> User:
    if not users.create(user):
        raise HTTPException(status_code=400, detail="Username already exists")
    return user


@router.post(
    "/createWithList", response_model_exclude_none=True, response_model_exclude={"password"}
)
def create_users_with_list(new_users: list[User], users: Users) -> list[User]:
    # Check every name first so a clash in the list doesn't leave half of it written.
    taken = [u.username for u in new_users if users.get(u.username) is not None]
    names = [u.username for u in new_users]
    if taken or len(set(names)) != len(names):
        raise HTTPException(status_code=400, detail="Username already exists")
    for user in new_users:
        users.create(user)
    return new_users


@router.get("/{username}", response_model_exclude_none=True)
def get_user_by_name(username: str, users: Users) -> User:
    user = users.get(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{username}")
def update_user(username: str, user: User, users: Users, caller: CallerName = None) -> None:
    _require_self(caller, username)
    # The path names the account; a username in the body can't rename it.
    if not users.update(user.model_copy(update={"username": username})):
        raise HTTPException(status_code=404, detail="User not found")


@router.delete("/{username}")
def delete_user(username: str, users: Users, caller: CallerName = None) -> dict[str, str]:
    _require_self(caller, username)
    if not users.delete(username):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}
