
from typing import Optional
from pydantic import BaseModel

from src.management_api.models.apikeys import ApiKeysModel


class AccountUpdate(BaseModel):
    uuid: str
    first_name: str | None = None
    second_name: str | None = None
    surname: str | None = None
    email: str | None = None
    cell: str | None = None
    is_admin: bool | None = None
    is_deleted: bool | None = None


class AccountCreate(BaseModel):
    first_name: str
    second_name: str | None = None
    surname: str
    email: str
    cell: str
    password: str
    is_admin: bool | None = False
    is_deleted: bool | None = False


class UserResponseSchema(BaseModel):
    status: bool
    payload: Optional[AccountUpdate]
    message: str


class DeleteResponseSchema(BaseModel):
    status: bool = True
    message: str


class LoginResponseSchema(BaseModel):
    uuid: str
    first_name: str
    second_name: str | None
    surname: str
    email: str
    cell: str
    password: str
    is_admin: bool | None
    is_deleted: bool | None
    apikeys: ApiKeysModel


class UsersResponseSchema(BaseModel):
    status: bool = True
    payload: list[LoginResponseSchema]
    message: str
