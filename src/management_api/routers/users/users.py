from fastapi import APIRouter, HTTPException, Request
from starlette.responses import JSONResponse

from src.config import config_instance
from src.const import UUID_LEN
from src.database.account.account import Account
from src.database.database_sessions import sessions
from src.management_api.email.email import email_process
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.management_api.models.users import AccountUpdate, AccountCreate, UserResponseSchema, DeleteResponseSchema, \
    UsersResponseSchema
from src.utils.my_logger import init_logger
from src.utils.utils import create_id

users_router = APIRouter()
users_logger = init_logger("users_router")


@users_router.api_route(path="/user", methods=["POST"], include_in_schema=True)
@authenticate_app
async def create_user(user_data: AccountCreate, request: Request) -> UserResponseSchema:
    """
    **create user**
        used to create new user record

    :param request:
    :param user_data: data containing user information

    :return: status payload, message -> see Responses
    """
    users_logger.info(f"creating user : {user_data}")
    with next(sessions) as session:
        users_logger.info(f"creating user with the following user data : {user_data}")
        email = user_data.email
        user_instance = await Account.get_by_email(email=email, session=session)
        if not user_instance:
            user_dict = user_data.dict()
            user_dict.update(uuid=create_id(UUID_LEN))
            user_instance = Account(**user_dict)
            session.add(user_instance)
            session.commit()
            # this will schedule an account confirmation email to be sent
            # TODO look at this - Make this an ephemeral link, it other words it should expire after sometime
            verification_link = f"https://gateway.eod-stock-api.site/_admin/account/confirm/{user_dict.get('uuid')}"

            sender_email = config_instance().EMAIL_SETTINGS.ADMIN
            recipient_email = user_instance.email
            client_name = user_instance.names
            message_dict = dict(verification_link=verification_link, sender_email=sender_email,
                                recipient_email=recipient_email, client_name=client_name)

            await email_process.send_account_confirmation_email(**message_dict)
            payload = dict(status=True, payload=user_instance.to_dict(), message="successfully created account")
            _headers = await get_headers(user_data=payload)
            return JSONResponse(content=payload, status_code=201, headers=_headers)

        else:
            # TODO create custom Exceptions
            raise HTTPException(detail="User already exist", status_code=401)


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
        updated_dict = user_data.dict(exclude_unset=True)
        for field, value in updated_dict.items():
            setattr(user_instance, field, value)

        session.merge(user_instance)
        session.commit()

        payload = dict(status=True, payload=user_instance.to_dict(), message="account updated successfully")

        headers = await get_headers(user_data=payload)
        return JSONResponse(content=payload, status_code=201, headers=headers)


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
        users_logger.info("Get Delete USER")
        # TODO Send a Login Email

    payload = dict(status=True, payload=user_instance.to_dict(), message="user found")
    headers = await get_headers(user_data=payload)
    return JSONResponse(content=payload, status_code=201, headers=headers)


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
        user_instance.is_deleted = True
        session.merge(user_instance)
        session.commit()
        # TODO send a Goodbye Email
        message = {'message': 'successfully deleted user'}
        headers = await get_headers(user_data=message)
        return JSONResponse(content=message,
                            status_code=201,
                            headers=headers)


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

