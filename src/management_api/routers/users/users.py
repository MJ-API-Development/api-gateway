import re

import pymysql.err
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from src.config import config_instance
from src.database.account.account import Account
from src.database.database_sessions import sessions
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.management_api.email.email import email_process
from src.management_api.models.users import AccountUpdate, AccountCreate, UserResponseSchema, DeleteResponseSchema, \
    UsersResponseSchema
from src.utils.my_logger import init_logger

users_router = APIRouter()
users_logger = init_logger("users_router")


# noinspection PyUnusedLocal
@users_router.api_route(path="/user", methods=["POST"], include_in_schema=True)
@authenticate_app
async def create_user(new_user: AccountCreate, request: Request) -> UserResponseSchema:
    """
    **create user**
        used to create new user record

    :param request:
    :param new_user: data containing user information

    :return: status payload, message -> see Responses
    """
    users_logger.info(f"Creating user : {new_user.dict()}")
    with next(sessions) as session:
        email: str = new_user.email
        user_instance: Account | None = await Account.get_by_email(email=email, session=session)

        if isinstance(user_instance, Account) and bool(user_instance):
            users_logger.info(f'User Found: ')
            payload = dict(status=False, payload={}, message="Error User Already Exists - Please login to proceed")
            _headers = await get_headers(user_data=payload)
            return JSONResponse(content=payload, status_code=201, headers=_headers)

        new_user_instance: Account = Account(**new_user.dict())
        if not bool(new_user_instance):
            users_logger.error(f'User Not Created: ')
            payload = dict(status=False, payload={}, message="Error Unable to create User - Please try again later")
            _headers = await get_headers(user_data=payload)
            return JSONResponse(content=payload, status_code=401, headers=_headers)

        users_logger.info(f'Saving User To DATABASE: ')
        try:
            session.add(new_user_instance)
            session.commit()
        except pymysql.err.IntegrityError as e:
            duplicate_data = re.findall(r"\+(\d+)", e)[0]
            message: str = f"Cannot Accept  {duplicate_data} as it is already used, by another user"
            payload = dict(status=False, payload={}, message=message)
            _headers = await get_headers(user_data=payload)
            return JSONResponse(content=payload, status_code=401, headers=_headers)

        session.flush()

        users_logger.info(f'Converting to dict: ')
        _payload: dict[str, str | dict[str, str]] = new_user_instance.to_dict()
        users_logger.info(f"Created NEW USER : {_payload}")

        # this will schedule an account confirmation email to be sent
        verification_link: str = f"https://gateway.eod-stock-api.site/_admin/account/confirm/{new_user_instance.uuid}"

        sender_email: str = config_instance().EMAIL_SETTINGS.ADMIN
        recipient_email: str = new_user_instance.email
        client_name: str = new_user_instance.names
        message_dict: dict[str, str] = dict(verification_link=verification_link, sender_email=sender_email,
                                            recipient_email=recipient_email, client_name=client_name)
        try:
            users_logger.info(f'Sending confirmation email : {message_dict}')
            await email_process.send_account_confirmation_email(**message_dict)
        except Exception as e:
            users_logger.info(f'Failed to send confirmation email : {message_dict}')

        payload: dict[str, str] = dict(status=True, payload=_payload, message="Successfully Created Account - Please Login to Proceed")
        _headers = await get_headers(user_data=payload)
        return JSONResponse(content=payload, status_code=201, headers=_headers)


# noinspection PyUnusedLocal
@users_router.api_route(path="/user", methods=["PUT"], include_in_schema=True)
@authenticate_app
async def update_user(user_data: AccountUpdate, request: Request) -> UserResponseSchema:
    """
    **update_user**
        given some fields on user_data update the user instance with those fields

    param: user_data: {dict}

    return: status: {boolean}, payload: {dict}, message: {string}
    """
    with next(sessions) as session:
        uuid = user_data.uuid
        user_instance: Account = await Account.get_by_uuid(uuid=uuid, session=session)
        if not bool(user_instance):
            payload = dict(status=True, payload={}, message="Unable to update account")
            headers = await get_headers(user_data=payload)
            return JSONResponse(content=payload, status_code=401, headers=headers)

        updated_dict = user_data.dict(exclude_unset=True)
        for field, value in updated_dict.items():
            setattr(user_instance, field, value)

        session.merge(user_instance)
        session.commit()
        session.flush()

        payload = dict(status=True, payload=user_instance.to_dict(), message="account updated successfully")

        headers = await get_headers(user_data=payload)
        return JSONResponse(content=payload, status_code=201, headers=headers)


# noinspection PyUnusedLocal
@users_router.api_route(path="/user/{uuid}", methods=["GET"], include_in_schema=True)
@authenticate_app
async def get_user(uuid: str, request: Request) -> UserResponseSchema:
    """
    **get_user**
        will retrieve user data
    :param request:
    :param uuid:
    :return: UserResponseSchema
    """
    with next(sessions) as session:
        user_instance: Account = await Account.get_by_uuid(uuid=uuid, session=session)

        if not bool(user_instance):
            payload = dict(status=True, payload={}, message="Unable to get account")
            headers = await get_headers(user_data=payload)
            return JSONResponse(content=payload, status_code=401, headers=headers)

        user_dict = user_instance.to_dict()
        users_logger.info(f"user found : {user_dict}")

    payload = dict(status=True, payload=user_dict, message="user found")
    headers = await get_headers(user_data=payload)
    return JSONResponse(content=payload, status_code=200, headers=headers)


# noinspection PyUnusedLocal
@users_router.api_route(path="/user/{uuid}", methods=["DELETE"], include_in_schema=True)
@authenticate_app
async def delete_user(uuid: str, request: Request) -> DeleteResponseSchema:
    """
        **delete_user**
            used to mark a user as deleted
    :return: DeleteResponseSchema
    """
    with next(sessions) as session:
        user_instance: Account = await Account.get_by_uuid(uuid=uuid, session=session)
        if not bool(user_instance):
            payload = dict(status=True, payload={}, message="Unable to find account")
            headers = await get_headers(user_data=payload)
            return JSONResponse(content=payload, status_code=401, headers=headers)

        user_instance.is_deleted = True
        session.merge(user_instance)
        session.commit()
        session.flush()
        # TODO send a Goodbye Email
        message = {'message': 'successfully deleted user'}
        headers = await get_headers(user_data=message)
        return JSONResponse(content=message,
                            status_code=201,
                            headers=headers)


# noinspection PyUnusedLocal
@users_router.api_route(path="/users", methods=["GET"], include_in_schema=True)
@authenticate_app
async def get_all_users(request: Request) -> UsersResponseSchema:
    """
        **delete_user**
            will return a complete list of all users of the api

    :return: dict of status: boolean, list of users, and message indicating how the operation went
    """
    with next(sessions) as session:
        users_list: Account = await Account.fetch_all(session=session)
        users = [AccountUpdate.from_orm(user) for user in users_list]
        payload = dict(status=True, payload=[user.dict() for user in users], message='successfully fetched all user')

        headers = await get_headers(user_data=payload)
        return JSONResponse(content=payload,
                            status_code=201,
                            headers=headers)


# noinspection PyUnusedLocal
@users_router.api_route(path="/users/subscription/{is_active}", methods=["GET"], include_in_schema=True)
@authenticate_app
async def get_users_by_subscription_status(is_active: bool, request: Request) -> UsersResponseSchema:
    """
        **get users by subscription status**
            accepts status to filter subscriptions by

    :return: dict of status: boolean, list of users, and message indicating how the operation went
    """
    status = bool(is_active)
    with next(sessions) as session:
        users_list: Account = await Account.fetch_all(session=session)
        users_list = [user for user in users_list if user.apikey.is_active == status]
        payload = dict(status=True, payload=[user.dict() for user in users_list],
                       message=f'successfully fetched all user by status = {status}')

        headers = await get_headers(user_data=payload)
        return JSONResponse(content=payload,
                            status_code=201,
                            headers=headers)
