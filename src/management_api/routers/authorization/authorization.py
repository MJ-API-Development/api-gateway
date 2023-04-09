from fastapi import APIRouter, Request
import asyncio
import hmac
import random
import string
from starlette.responses import JSONResponse

from src.cache.cache import redis_cache
from src.database.account.account import Account, TwoFactorLoginData
from src.database.database_sessions import sessions
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.management_api.email.email import email_process
from src.management_api.models.authentication import LoginData, AuthorizationRequest
from src.utils.my_logger import init_logger

auth_router = APIRouter()

auth_logger = init_logger("auth_logger")


async def check_authorization(uuid: str | None, path: str, method: str) -> bool:
    """
    Function to check if user is authorized to access a specific route.
    Assume there is a map containing routes which normal users can access
    and routes that only admin users can access.
    :param uuid: The user's UUID.
    :param path: The path being accessed.
    :param method: The HTTP method being used.
    :return: True if the user is authorized, False otherwise.
    """
    # Map containing routes accessible by normal users and admin users
    user_routes = {
        "/home": ["GET"],
        "/account": ["GET", "PUT", "POST", "DELETE"],
        "/account/two-factor": ["GET", "PUT", "POST"],
        "/profile": ["GET", "PUT"],
        "/user": ["GET", "PUT", "POST"],
        "/auth/authorize": ["POST"],
        "/auth/login": ["GET"],
        "/logout": ["GET"],
        "/login": ["GET", "POST"]
    }

    admin_routes = {
        "/dashboard/users": ["GET", "POST", "PUT", "DELETE"],
        "/dashboard/subscriptions": ["GET", "POST", "PUT", "DELETE"],
        "/dashboard/plans": ["GET", "POST", "PUT", "DELETE"],
        "/home": ["GET"],
        "/account": ["GET", "PUT", "POST", "DELETE"],
        "/account/two-factor": ["GET", "PUT", "POST"],
        "/profile": ["GET", "PUT"],
        "/user": ["GET", "PUT", "POST"],
        "/auth/authorize": ["POST"],
        "/auth/login": ["GET"],
        "/logout": ["GET"],
        "/login": ["GET", "POST"]
    }

    if uuid is None or path is None or method is None:
        return False

    auth_logger.info(f"Authorizing Path : {path} for uuid : {uuid}")
    # Retrieve the user data based on the UUID
    with next(sessions) as session:
        user = await Account.get_by_uuid(uuid=uuid, session=session)

    # Check if the user is authorized to access the path
    if user is None:
        return False

    if path in user_routes and method.capitalize() in user_routes[path]:
        return True

    if user.is_admin and path in admin_routes and method.capitalize() in admin_routes[path]:
        # Check if the path is accessible only to admin users
        return True


@auth_router.api_route(path="/auth/login", methods=["POST"], include_in_schema=True)
@authenticate_app
async def login(login_data: LoginData, request: Request):
    """
        used to update a user
    :param request:
    :param login_data:
    :return:
    """
    user_data: dict[str, str] = login_data.dict()
    email = user_data.get("email")
    password = user_data.get("password")
    auth_logger.info(f"login into account : {email}")
    with next(sessions) as session:
        user_instance = await Account.login(username=email, password=password, session=session)
        auth_logger.info(f"user instance : {user_instance.to_dict()}")
        if user_instance:
            # Once the user is logged in generate and send two factor auth
            code = await generate_and_send_two_factor_code(email=email)
            two_factor_key = f"two_factor_code_{user_instance.to_dict().get('uuid')}"
            # Two factor authentication will expire after 5 minutes
            await redis_cache.set(key=two_factor_key, value=code, ttl=60*5)

            payload = dict(status=True, payload=user_instance.to_dict(), message="successfully logged in")
        else:
            payload = dict(status=False, payload={}, message="user not found")
    headers = await get_headers(user_data=user_instance.to_dict())

    return JSONResponse(content=payload, status_code=200, headers=headers)


@auth_router.api_route(path="/auth/login/two-factor", methods=["POST"], include_in_schema=True)
async def authenticate_two_factor(two_factor_data: TwoFactorLoginData, request: Request):
    """
    Endpoint to authenticate two-factor authentication code.
    if code does not authenticate in five minutes then the client app will not login the user

    :param two_factor_data: TwoFactorLoginData - data containing user's email and two-factor authentication code
    :param request: Request - the incoming request
    :return: JSONResponse - a response containing the login status and user data
    """
    user_data: dict[str, str] = two_factor_data.dict()
    email = user_data.get("email")
    code = user_data.get("code")
    auth_logger.info(f"authenticating two-factor code for account: {email}")

    with next(sessions) as session:
        # Retrieve the two-factor authentication key stored in Redis
        user_instance = await Account.get_by_email(email, session=session)

        two_factor_key = f"two_factor_key_{user_instance.to_dict().get('uuid')}"
        stored_key = await redis_cache.get(two_factor_key)
        if stored_key is None:
            payload = dict(status=False, payload={}, message="Authentication key Expired")
            return JSONResponse(content=payload, status_code=401)

        # Use HMAC to compare the user's input key with the stored key
        stored_key_bytes = stored_key.encode('utf-8')
        code_bytes = code.encode('utf-8')

        if not hmac.compare_digest(stored_key_bytes, code_bytes):
            # Authentication failed
            payload = dict(status=False, payload={}, message="invalid two-factor authentication key")
            return JSONResponse(content=payload, status_code=401)

        # Authentication succeeded
        user_instance = await Account.get_by_email(email)

    payload = dict(status=True, payload=user_instance.to_dict(), message="successfully authenticated two-factor")
    headers = await get_headers(user_data=user_instance.to_dict())
    return JSONResponse(content=payload, status_code=200, headers=headers)


@auth_router.api_route(path="/auth/authorize", methods=["POST"], include_in_schema=True)
@authenticate_app
async def authorization(auth_data: AuthorizationRequest, request: Request):
    """
    **authorization**
        authorizes requests to specific resources within the admin application

    :type request: Request
    :param request:
    :type auth_data: AuthorizationRequest
    :param auth_data: authorization data class
    :type payload: dict
    :return: payload : dict[str, str| bool dict[str|bool]], status_code
    """
    data = auth_data.dict()
    uuid = data.get("uuid")
    path = data.get("path")
    method = data.get("method")

    is_authorized = await check_authorization(uuid=uuid, path=path, method=method)
    message = "user is authorized" if is_authorized else "user not authorized"
    payload = dict(status=True, payload=dict(is_authorized=is_authorized), message=message)
    headers = await get_headers(user_data=payload)
    return JSONResponse(content=payload, status_code=200, headers=headers)


async def generate_and_send_two_factor_code(email: str) -> str:
    """
    Generate a two-factor code and schedule an email to be sent later.
    Returns the generated code.
    """
    # Generate a random code
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Add the code and email to the queue
    await email_process.send_two_factor_code_email(email=email, code=code)

    return code
