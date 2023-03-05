import asyncio

from src.cache.cache import redis_cache
from src.prefetch.dynamic_urls import build_dynamic_urls
from src.requests import requester


async def prefetch_endpoints():
    """will fetch the endpoints causing the endpoints to be cached"""
    urls = await build_dynamic_urls()
    responses = await asyncio.gather(*[requester(_url) for _url in urls])
    for response, url in zip(responses, urls):
        if response and response.get("status"):
            await redis_cache.set(key=url, value=response)
