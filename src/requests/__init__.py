import httpx
from src.config import config_instance

# Use the connection pool limits in the AsyncClient

_headers = {
    'X-API-KEY': config_instance().API_SERVERS.X_API_KEY,
    'X-SECRET-TOKEN': config_instance().API_SERVERS.X_SECRET_TOKEN,
    'X-RapidAPI-Proxy-Secret': config_instance().API_SERVERS.X_RAPID_SECRET,
    'Content-Type': "application/json",
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
}

async_client = httpx.AsyncClient(http2=True,
                                 limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                                 headers=_headers)


async def requester(api_url: str, timeout: int = 30):
    """
        30 seconds is the maximum amount of time a request will ever wait
    :param api_url:
    :param timeout:
    :return:
    """
    try:
        response = await async_client.get(url=api_url, timeout=timeout)
    except httpx.HTTPError as http_err:
        raise http_err
    except Exception as err:
        raise err
    return response.json() if response else None

