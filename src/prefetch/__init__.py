import asyncio

import httpx

from src.prefetch.dynamic_urls import build_dynamic_urls
from src.requests import requester


async def prefetch_endpoints():
    """will fetch the endpoints causing the endpoints to be cached"""
    urls = await build_dynamic_urls()
    tasks = await asyncio.gather(*[requester(_url) for _url in urls])
