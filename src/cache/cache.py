import asyncio
import functools
from src.cache.custom import Cache


async def create_key(method: str, kwargs: dict[str, str | int]) -> str:
    """
        used to create keys for cache redis handler
    """
    if not kwargs:
        _key = "all"
    else:
        _key = ".".join(f"{key}={str(value)}" for key, value in kwargs.items() if value).lower()
    return f"{method}.{_key}"


def redis_cached_ttl(ttl: int = 60 * 60 * 1):
    """
    Caching decorator with a time-to-live (TTL) parameter that stores the function's return value in Redis for fast retrieval
    and sets an expiration time for the cached value.
    """

    def _redis_cached(func):
        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):

            api_url, = args if args else None
            new_kwargs = {'api_url': api_url} if api_url is not None else {}
            new_kwargs.update({k: v for k, v in kwargs.items() if k != 'session'})
            _key = await create_key(method=func.__name__, kwargs=new_kwargs)

            _data = await redis_cache.get(_key)
            if _data is None:
                result = await func(*args, **kwargs)
                if result:
                    await redis_cache.set(key=_key, value=result, ttl=ttl)
                return result
            return _data

        return _wrapper

    return _redis_cached


redis_cache = Cache(cache_name="redis", use_redis=True)
asyncio.run(redis_cache.create_redis_pool())
# mem_cache = Cache(cache_name="mem_cache", use_redis=False)
