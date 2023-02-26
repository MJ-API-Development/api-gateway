import asyncio

from src.prefetch.dynamic_urls import build_dynamic_urls
from src.requests import requester


async def prefetch_endpoints():
    """will fetch the endpoints causing the endpoints to be cached"""
    for endpoint in build_dynamic_urls():
        response = await requester(endpoint)
        await asyncio.sleep(5)
