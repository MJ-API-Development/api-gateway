import time
from functools import wraps

from fastapi import HTTPException
from starlette import status

from src.apikeys.keys import api_keys, cache_api_keys

RATE_LIMIT = 5000
RATE_LIMIT_DURATION = 60 * 60 * 24


def auth_and_rate_limit():
    def decorator(func):
        # noinspection PyTypeChecker
        @wraps(func)
        async def wrapper(*args, **kwargs):
            api_key = kwargs.get('api_key')
            if api_key is not None:
                if api_key not in api_keys:
                    cache_api_keys()  # Update api_keys if the key is not found
                    if api_key not in api_keys:
                        # user not authorized to access this routes
                        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid API Key')

                now = time.time()
                duration = api_keys[api_key]['duration']
                limit = api_keys[api_key]['limit']

                if now - api_keys[api_key]['last_request_timestamp'] > duration:
                    api_keys[api_key]['requests_count'] = 0

                if api_keys[api_key]['requests_count'] >= limit:
                    # TODO consider returning a JSON String with data on the rate limit and how long to wait
                    raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Rate limit exceeded')

                # updating number of requests and timestamp
                api_keys[api_key]['requests_count'] += 1
                api_keys[api_key]['last_request_timestamp'] = now

            return await func(*args, **kwargs)

        return wrapper

    return decorator
