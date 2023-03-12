from fastapi import APIRouter

from starlette.responses import JSONResponse

from src.database.account.account import Account
from src.database.database_sessions import sessions
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.management_api.models.authentication import LoginData, AuthorizationRequest

auth_router = APIRouter()


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
        "/dashboard": ["GET", "PUT"],
        "/profile": ["GET", "PUT"]
    }
    admin_routes = {
        "/admin/users": ["GET", "POST", "PUT", "DELETE"],
        "/admin/subscriptions": ["GET", "POST", "PUT", "DELETE"],
        "/admin/plans": ["GET", "POST", "PUT", "DELETE"]
    }

    if uuid is None or path is None or method is None:
        return False

    # Retrieve the user data based on the UUID
    with next(sessions) as session:
        user = await Account.get_by_uuid(uuid=uuid, session=session)

    # Check if the user is authorized to access the path
    if user is None:
        return False

    if path in user_routes and method in user_routes[path]:
        return True

    if user.is_admin and path in admin_routes and method in admin_routes[path]:
        # Check if the path is accessible only to admin users
        return True


@auth_router.api_route(path="/auth/login", methods=["POST"], include_in_schema=True)
@authenticate_app
async def login(login_data: LoginData):
    """
        used to update a user

    :param login_data:
    :return:
    """
    user_data: dict[str, str] = login_data.dict()
    email = user_data.get("email")
    password = user_data.get("password")
    with next(sessions) as session:
        user_instance = await Account.login(username=email, password=password, session=session)
        if user_instance:
            payload = dict(status=True, payload=user_instance.to_dict(), message="successfully logged in")
        else:
            payload = dict(status=False, payload={}, message="user not found")
    headers = await get_headers(user_data=user_instance.to_dict())
    return JSONResponse(content=payload, status_code=200, headers=headers)


@auth_router.api_route(path="/auth/authorize", methods=["POST"], include_in_schema=True)
@authenticate_app
async def authorization(auth_data: AuthorizationRequest):
    """
    **authorization**
        authorizes requests to specific resources within the admin application

    :param auth_data: authorization data
    :return: payload : dict[str, str| bool dict[str|bool]], status_code
    """
    user_data = auth_data.dict()
    uuid = user_data.get("uuid")
    path = user_data.get("path")
    method = user_data.get("method")

    is_authorized = await check_authorization(uuid=uuid, path=path, method=method)
    message = "user is authorized" if is_authorized else "user not authorized"
    payload = dict(status=True, payload=dict(is_authorized=is_authorized), message=message)
    headers = await get_headers(user_data=payload)
    return JSONResponse(content=payload, status_code=200, headers=headers)
