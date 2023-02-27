from functools import wraps
from fastapi import requests

from src.apikeys.keys import ApiKeyModel, sessions
from src.cache.cache import cached_ttl


class NotAuthorized(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.status_code = 403


def authenticate_admin(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        api_key = kwargs.get("x-api-key")
        with next(sessions) as session:
            api_keys_model = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
            if api_keys_model.account.is_admin:
                return await func(*args, **kwargs)

        raise NotAuthorized(message="This Resource is only Accessible to Admins")

    return wrapper
