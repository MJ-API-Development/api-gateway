import asyncio

from src.cache.cache import redis_cache
from src.prefetch.dynamic_urls import build_dynamic_urls
from src.requests import requester


async def prefetch_endpoints() -> int:
    """will fetch the endpoints causing the endpoints to be cached"""
    urls = await build_dynamic_urls()
    # will wait for a maximum of 30 seconds for a response
    i = 0
    for url in urls:
        response = await requester(api_url=url, timeout=60*5)
        if response and response.get("status", False):
            await redis_cache.set(key=url, value=response)
        #  this enables the gateway to process other requests while still prefetching urls
        await asyncio.sleep(delay=3)
        i += 1
    return i
