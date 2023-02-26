# Prefetch endpoints
from itertools import chain

from src.main.main import api_server_urls
from src.requests import requester

PREFETCH_ENDPOINTS = [
    '/api/v1/exchanges',
    '/api/v1/stocks',
    '/api/v1/fundamental/general']


async def get_exchange_lists():
    server_url = api_server_urls[0]
    api_url = f"{server_url}/api/v1/exchanges"
    response = await requester(api_url=api_url)
    data = response.json()
    if data.get("status"):
        return data.get("payload")
    return {}


async def get_exchange_codes():
    return [exchange.get("code") for exchange in await get_exchange_lists()]


async def get_exchange_ids():
    return [exchange.get("exchange_id") for exchange in await get_exchange_lists()]


async def get_currencies():
    return [exchange.get("currency_symbol") for exchange in await get_exchange_lists()]


async def get_countries():
    return [exchange.get("country") for exchange in await get_exchange_lists()]


async def build_dynamic_urls() -> list[str]:
    """
        dynamic urls to prefetch
    :return:
    """
    codes_urls = ['/api/v1/exchange/listed-stocks/',
                  '/api/v1/stocks/exchange/code/']
    exchange_by_id_url = "/api/v1/stocks/exchange/id/"
    stocks_by_currency_url = "/api/v1/stocks/currency/"
    stocks_by_country_url = "/api/v1/stocks/country/"
    expanded_urls = []
    for server_url in api_server_urls:
        for endpoint in codes_urls:
            for code in await get_exchange_codes():
                expanded_urls.append(f"{server_url}{endpoint}{code}")
        for _id in await get_exchange_ids():
            expanded_urls.append(f"{server_url}{exchange_by_id_url}{_id}")
        for _currency in await get_currencies():
            expanded_urls.append(f"{server_url}{stocks_by_currency_url}{_currency}")
        for _country in await get_countries():
            expanded_urls.append(f"{server_url}{stocks_by_country_url}{_country}")
    urls = list(chain(*[expanded_urls, PREFETCH_ENDPOINTS]))
    return urls
