from functools import wraps
from fastapi import FastAPI, Request

from src.apikeys.keys import ApiKeyModel, sessions
from src.authorize.authorize import NotAuthorized
from src.cache.cache import cached_ttl


def authenticate_admin(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs.get('request')
        api_key = request.query_params.get('api_key')
        with next(sessions) as session:
            api_keys_model = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
            if api_keys_model.account.is_admin:
                return await func(*args, **kwargs)

        raise NotAuthorized(message="This Resource is only Accessible to Admins")

    return wrapper
