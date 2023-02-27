import asyncio

import httpx

from src.prefetch.dynamic_urls import build_dynamic_urls
from src.requests import requester


async def prefetch_endpoints():
    """will fetch the endpoints causing the endpoints to be cached"""
    for endpoint in await build_dynamic_urls():
        try:
            response = await requester(endpoint)
        except httpx.HTTPError as e:
            # TODO log error messages
            pass
        # await asyncio.sleep(5)
