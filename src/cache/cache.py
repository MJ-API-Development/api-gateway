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


def cached(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        new_kwargs = kwargs.copy()
        for key, value in kwargs.items():
            if key == 'session':
                # removing session from keys
                _ = new_kwargs.pop(key)
        if args:
            api_url, = args
            new_kwargs.update(dict(api_url=api_url))
        _key = await create_key(method=func.__name__, kwargs=new_kwargs)

        _data = await mem_cache.get(_key)
        if _data is None:
            result = await func(*args, **kwargs)
            if result:
                await mem_cache.set(key=_key, value=result)
                # redis_cache.set(key=_key, value=result, expiration_time=60*60*1)
            return result
        return _data

    return wrapper


def cached_ttl(ttl: int = 60 * 60 * 1):
    def _cached(func):
        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):
            new_kwargs = kwargs.copy()
            for key, value in kwargs.items():
                if key == 'session':
                    # removing session from keys
                    _ = new_kwargs.pop(key)

            if args:
                api_url, = args
                new_kwargs.update(dict(api_url=api_url))

            _key = await create_key(method=func.__name__, kwargs=new_kwargs)
            _data = await mem_cache.get(_key)
            if _data is None:
                result = await func(*args, **kwargs)
                if result:
                    await mem_cache.set(key=_key, value=result)
                    # redis_cache.set(key=_key, value=result, expiration_time=60*60*1)
                return result
            return _data
        return _wrapper

    return _cached


# Set Use redis to false temporarily

redis_cache = Cache(cache_name="redis", use_redis=True)
mem_cache = Cache(cache_name="mem_cache", use_redis=False)
