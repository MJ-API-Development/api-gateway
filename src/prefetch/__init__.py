import asyncio

from src.cache.cache import redis_cache
from src.prefetch.dynamic_urls import build_dynamic_urls
from src.requests import requester


async def prefetch_endpoints() -> int:
    """will fetch the endpoints causing the endpoints to be cached"""
    urls = await build_dynamic_urls()
    # will wait for a maximum of 30 seconds for a response
    responses = await asyncio.gather(*[requester(_url, timeout=3) for _url in urls])

    for response, url in zip(responses, urls):
        if response and response.get("status", False):
            await redis_cache.set(key=url, value=response)
        #  this enables the gateway to process other requests while still prefetching urls
        await asyncio.sleep(delay=3)

    return len(responses)
