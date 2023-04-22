"""
    This Module is responsible with route authorization
"""

import re

from src.database.account.account import Account
from src.database.database_sessions import sessions
from src.utils.my_logger import init_logger

auth_logger = init_logger("auth_logger")

ALLOWED_ROUTES = {
    "regular": {
        "/home": ["GET"],
        "/account": ["GET", "PUT", "POST", "DELETE"],
        "/account/two-factor": ["GET", "PUT", "POST"],
        "/profile": ["GET", "PUT"],
        "/user": ["GET", "PUT", "POST"],
        "/auth/authorize": ["POST"],
        "/auth/login": ["GET"],
        "/logout": ["GET"],
        "/login": ["GET", "POST"],
        r"/account/\w+": ["GET", "PUT", "DELETE"],
        "/update-api-key": ["POST"]
    },
    "admin": {
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
        "/login": ["GET", "POST"],
        r"/account/\w+": ["GET", "PUT", "POST", "DELETE"],
        "/update-api-key": ["POST"]
    }
}


async def check_authorization(uuid: str | None, path: str, method: str) -> bool:
    """
    Function to check if user is authorized to access a specific route based on their role.
    :param uuid: The user's UUID.
    :param path: The path being accessed.
    :param method: The HTTP method being used.
    :return: True if the user is authorized, False otherwise.
    """
    # Load the allowed routes for the user's role
    if uuid is None or path is None or method is None:
        return False

    auth_logger.info(f"Authorizing Path : {path} and Method: {method}, for UUID : {uuid}")
    # Retrieve the user data based on the UUID
    with next(sessions) as session:
        user: Account | None = await Account.get_by_uuid(uuid=uuid, session=session)

    if user is None:
        return False

    auth_logger.info(f"User is found for authorization: user: {user.uuid}")

    routes: dict[str, list[str]] = ALLOWED_ROUTES["admin"] if user.is_admin else ALLOWED_ROUTES["regular"]
    method: str = method.upper()
    # Check if the requested path matches any of the regular expressions in the dictionary
    for route, methods in routes.items():
        if re.match(route, path) and method in methods:
            return True

    auth_logger.info(f"User : {uuid} is Not Authorized to access path : {path}")
    return False
