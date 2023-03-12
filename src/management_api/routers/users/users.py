
from fastapi import APIRouter, Request, HTTPException
from starlette.responses import JSONResponse

from src.config import config_instance
from src.database.account.account import Account
from src.database.database_sessions import sessions
from src.email.email import email_process
from src.management_api.admin.authentication import authenticate_app, get_headers

from src.utils.my_logger import init_logger

users_router = APIRouter()
users_logger = init_logger("users_router")


@users_router.api_route(path="/user", methods=["POST", "PUT"], include_in_schema=True)
@authenticate_app
async def create_update_user(request: Request, user_data: dict[str, str | int | bool]):
    """
        used to create new user record
    :param user_data:
    :param request:
    :return:
    """
    headers = {'Content-Type': 'application/json'}
    with next(sessions) as session:
        if request.method == "POST":
            users_logger.info("create user")
            email = user_data.get("email")
            user_instance = await Account.get_by_email(email=email, session=session)
            if not user_instance:
                user_instance = Account(**user_data)
                session.add(user_instance)
                account_dict = dict()
                # this will schedule an account confirmation email to be sent
                # TODO look at this - Make this an ephemeral link, it other words it should expire after sometime
                verification_link = f"https://gateway.eod-stock-api.site/_admin/account/confirm/{account_dict.get('uuid')}"

                sender_email = config_instance().EMAIL_SETTINGS.ADMIN
                recipient_email = account_dict.get('email')
                client_name = account_dict.get('name')
                message_dict = dict(verification_link=verification_link, sender_email=sender_email,
                                    recipient_email=recipient_email, client_name=client_name)

                await email_process.send_account_confirmation_email(**message_dict)
            else:
                raise HTTPException(detail="User already exist", status_code=401)

        elif request.method == "PUT":
            uuid = user_data.get('uuid')
            user_instance = await Account.get_by_uuid(uuid=uuid, session=session)
            user_instance = user_instance(**user_data)
            session.merge(user_instance)

        session.commit()
        headers = await get_headers(user_data=user_instance.to_dict())
        return JSONResponse(content=user_instance.to_dict(), status_code=201, headers=headers)


@users_router.api_route(path="/user/{path}", methods=["GET", "DELETE"], include_in_schema=True)
@authenticate_app
async def get_delete_user(request: Request, path: str):
    """
        used to update a user
    :param request:
    :param path:
    :return:
    """
    users_logger.info("Get Delete USER")

    uuid: str = path
    with next(sessions) as session:
        user_instance: Account = await Account.get_by_uuid(uuid=uuid, session=session)
        if request.method == "DELETE":
            user_instance.is_deleted = True
            session.merge(user_instance)
            session.commit()
            # TODO send a Goodbye Email
            message = {'message': 'successfully deleted user'}
            headers = await get_headers(user_data=message)
            return JSONResponse(content=message,
                                status_code=201,
                                headers=headers)

        elif request.method == "GET":
            # TODO Send a Login Email
            headers = await get_headers(user_data=user_instance.to_dict())
            return JSONResponse(content=user_instance.to_dict(),
                                status_code=201,
                                headers=headers)

    message = {'message': 'successfully deleted user'}
    headers = await get_headers(user_data=message)
    return JSONResponse(content={'message': 'deleted user'}, status_code=201, headers=headers)

