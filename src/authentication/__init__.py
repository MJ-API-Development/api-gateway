import hashlib
from functools import wraps
from fastapi import Request
import hmac
from src.config import config_instance
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
        if await verify_signature(request=request):
            return await func(*args, **kwargs)

        raise NotAuthorized(message="This Resource is only Accessible to Admins")

    return wrapper


def authenticate_cloudflare_workers(func):
    @wraps(func)
    async def _cloudflare_auth(*args, **kwargs):
        request: Request = kwargs.get('request')
        secret_token = request.headers.get('X-SECRET-KEY')
        this_secret_token = config_instance().CLOUDFLARE_SETTINGS.CLOUDFLARE_SECRET_KEY

        if hmac.compare_digest(this_secret_token, secret_token):
            return await func(*args, **kwargs)
        else:
            raise NotAuthorized(message="Invalid X-SECRET-KEY header")

    return _cloudflare_auth


async def verify_signature(request):
    secret_key = config_instance().SECRET_KEY
    request_header = request.headers.get('X-SIGNATURE', '')
    data_str, signature_header = request_header.split('|')
    _signature = hmac.new(secret_key.encode(), data_str, hashlib.sha256).hexdigest()
    return hmac.compare_digest(_signature, signature_header)
