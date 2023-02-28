import httpx
from src.config import config_instance
from src.cache.cache import cached

# Use the connection pool limits in the AsyncClient
async_client = httpx.AsyncClient(http2=True)


@cached
async def requester(api_url: str):
    try:
        headers = await set_headers()
        # response = await async_client.get(api_url, headers=headers)
        response = await async_client.get(api_url, headers=headers)
        response.raise_for_status()
    except httpx.HTTPError as http_err:
        raise http_err
    except Exception as err:
        raise err
    return response


@cached
async def set_headers():
    return {'X-API-KEY': config_instance().API_SERVERS.X_API_KEY,
            'X-SECRET-TOKEN': config_instance().API_SERVERS.X_SECRET_TOKEN,
            'X-RapidAPI-Proxy-Secret': config_instance().API_SERVERS.X_RAPID_SECRET,
            'Content-Type': "application/json",
            'Host': "https://eod-stock-api.site",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; 64)'}

# TODO Try random election
