# Prefetch endpoints

from itertools import chain
from httpx import HTTPError
from src.config import config_instance
from src.prefetch.exchange_lists import cached_exchange_lists
from src.requests import requester
from src.views_cache.cache import cached_ttl

ONE_DAY = 60 * 60 * 24

api_server_urls = [config_instance().API_SERVERS.MASTER_API_SERVER, config_instance().API_SERVERS.SLAVE_API_SERVER]

PREFETCH_ENDPOINTS = [
    '/api/v1/exchanges',
    '/api/v1/stocks',
    '/api/v1/fundamental/general']


async def get_exchange_lists():
    server_url = api_server_urls[0]
    api_url = f"{server_url}/api/v1/exchanges"
    try:
        _response = await requester(api_url=api_url)
        data = _response.json()
        if data.get("status"):
            return data.get("payload")
    except HTTPError:
        pass
    return cached_exchange_lists


async def get_exchange_codes():
    return [exchange.get("code") for exchange in await get_exchange_lists()]


async def get_exchange_ids():
    return [exchange.get("exchange_id") for exchange in await get_exchange_lists()]


async def get_currencies():
    return [exchange.get("currency_symbol") for exchange in await get_exchange_lists()]


async def get_countries():
    return [exchange.get("country") for exchange in await get_exchange_lists()]


@cached_ttl(ttl=ONE_DAY)
async def build_dynamic_urls() -> list[str]:
    """
        dynamic urls to prefetch
    :return:
    """
    codes_urls = ['/api/v1/exchange/listed-stocks/', '/api/v1/stocks/exchange/code/']
    exchange_by_id_url = "/api/v1/stocks/exchange/id/"
    stocks_by_currency_url = "/api/v1/stocks/currency/"
    stocks_by_country_url = "/api/v1/stocks/country/"

    expanded_urls = []
    for server_url in api_server_urls:
        for endpoint in codes_urls:
            for code in await get_exchange_codes():
                if code and code != "null":
                    expanded_urls.append(f"{server_url}{endpoint}{code}")
        for _id in await get_exchange_ids():
            if _id and _id != "null":
                expanded_urls.append(f"{server_url}{exchange_by_id_url}{_id}")
        for _currency in await get_currencies():
            if _currency and _currency != "null":
                expanded_urls.append(f"{server_url}{stocks_by_currency_url}{_currency}")
        for _country in await get_countries():
            if _country and _country != "null":
                expanded_urls.append(f"{server_url}{stocks_by_country_url}{_country}")

    return list(chain(*[expanded_urls, PREFETCH_ENDPOINTS]))


if __name__ == "__main__":
    import asyncio

    response = asyncio.run(build_dynamic_urls())
    print(response)
    print(f"total urls: {len(response)} ")
