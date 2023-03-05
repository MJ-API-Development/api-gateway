from functools import wraps
from fastapi import Request

from src.cache.cache import redis_cached_ttl
from src.database.account.account import Account
from src.database.apikeys.keys import ApiKeyModel, sessions
from src.authorize.authorize import NotAuthorized


# TODO find a way to cache the results of this methods
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


def authenticate_app(func):
    """
        this will only authenticate application example client and admin app
    :param func:
    :return:
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # TODO find a way of authenticating APPS, not BASED on API, Suggestion SECRET_KEY
        request: Request = kwargs.get('request')
        api_key = request.query_params.get('api_key')
        with next(sessions) as session:
            api_keys_model = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
            account_instance = await Account.get_by_uuid(api_keys_model.uuid, session=session)
            if account_instance.is_admin:
                return await func(*args, **kwargs)

        raise NotAuthorized(message="This Resource is only Accessible to Admins")

    return wrapper
