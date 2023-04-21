from typing import Optional
from pydantic import BaseModel, Field

from src.management_api.models.apikeys import ApiKeysModel
from src.utils.utils import create_id


class AccountUpdate(BaseModel):
    uuid: str
    first_name: str | None = None
    second_name: str | None = None
    surname: str | None = None
    email: str | None = None
    cell: str | None = None
    is_admin: bool | None = None
    is_deleted: bool | None = None

    class Config:
        title = "Account Update Schema"


class AccountCreate(BaseModel):
    uuid: str | None = Field(default_factory=create_id)
    first_name: str
    second_name: str | None = None
    surname: str
    email: str
    cell: str
    password: str

    class Config:
        title = "Account Created Schema"


class UserResponseSchema(BaseModel):
    status: bool
    payload: Optional[AccountUpdate]
    message: str

    class Config:
        title = "User Response Schema"


class DeleteResponseSchema(BaseModel):
    status: bool = True
    message: str

    class Config:
        title = "Delete Response Schema"


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

    class Config:
        title = "Login Response Schema"


class UsersResponseSchema(BaseModel):
    status: bool = True
    payload: list[LoginResponseSchema]
    message: str

    class Config:
        title = "Users Response Schema"
