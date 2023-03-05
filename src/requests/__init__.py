import httpx
from src.config import config_instance
from src.cache.cache import cached
import requests

# Use the connection pool limits in the AsyncClient


async_client = httpx.AsyncClient(http2=True, limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))


async def requester(api_url: str):
    try:
        headers = await set_headers()
        response = await async_client.get(url=api_url, headers=headers, timeout=360000)
    except httpx.HTTPError as http_err:
        raise http_err
    except Exception as err:
        raise err
    return response.json()


async def set_headers():
    return {'X-API-KEY': config_instance().API_SERVERS.X_API_KEY,
            'X-SECRET-TOKEN': config_instance().API_SERVERS.X_SECRET_TOKEN,
            'X-RapidAPI-Proxy-Secret': config_instance().API_SERVERS.X_RAPID_SECRET,
            'Content-Type': "application/json",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}

# TODO Try random election
