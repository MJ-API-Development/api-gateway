from functools import wraps

import httpx
from aiocache import caches
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.apikeys.keys import cache_api_keys
from src.config import config_instance
from src.ratelimit.limit import auth_and_rate_limit

config = {
    "default": {
        "cache": "aiocache.SimpleMemoryCache",
        "serializer": {
            "class": "aiocache.serializers.PickleSerializer"
        },
        "ttl": 3600  # One Hour
    }
}

caches.set_config(config)
cache = caches.get("default")


def async_cache(function):
    @wraps(function)
    async def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        data = await cache.get(key)
        if data is None:
            # If data is not in the cache, execute the function to retrieve it
            data = await function(*args, **kwargs)
            # Store the data in the cache
            await cache.set(key, data)
        return data

    return wrapper


description = """

"""

app = FastAPI(
    title="EOD-STOCK-API - GATEWAY",
    description=description,
    version="1.0.0",
    terms_of_service="https://www.eod-stock-api.site/terms",
    contact={
        "name": "EOD-STOCK-API",
        "url": "https://eod-stock-api.site/contact",
        "email": "info@eod-stock-api.site"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# Use a background task to periodically update the `api_keys` dict
@app.on_event('startup')
async def startup_event():
    import asyncio

    async def update_api_keys_background_task():
        while True:
            cache_api_keys()
            # wait for 3 minutes then update API Keys records
            await asyncio.sleep(60 * 3)

    asyncio.create_task(update_api_keys_background_task())


api_server_urls = [config_instance().API_SERVERS.MASTER_API_SERVER, config_instance().API_SERVERS.SLAVE_API_SERVER]
api_server_counter = 0


@app.api_route("/api/v1/{path:path}", methods=["GET"])
@auth_and_rate_limit()
async def reroute_to_api_endpoint(request: Request, path: str):
    """
    NOTE: In order for the gateway server to work properly it needs at least 2 GIG or RAM
        master router
    :param request:
    :param path:
    :return:
    """
    global api_server_counter
    api_server_url = api_server_urls[api_server_counter]
    api_server_counter = (api_server_counter + 1) % len(api_server_urls)
    api_url = f'{api_server_url}/api/v1/{path}'

    response = await _request(api_url)
    # creating response
    headers = {"Content-Type": "application/json"}

    if 'application/json' not in response.headers['Content-Type']:
        message = "there was an error accessing server please tru again later, if this error persists please " \
                  "contact admin@eod-stock-api.site"
        return JSONResponse(content=dict(status=False, message=message), status_code=404, headers=headers)

    data = response.json()
    content = data
    status_code = response.status_code
    return JSONResponse(content=content, status_code=status_code, headers=headers)


# Use the connection pool limits in the AsyncClient
async_client = httpx.AsyncClient(http2=True)


@async_cache
async def _request(api_url: str):
    headers = await set_headers()
    #  the API must only return json data
    response = await async_client.get(api_url, headers=headers)
    return response


@async_cache
async def set_headers():
    return {'X-API-KEY': config_instance().API_SERVERS.X_API_KEY,
            'X-SECRET-TOKEN': config_instance().API_SERVERS.X_SECRET_TOKEN,
            'X-RapidAPI-Proxy-Secret': config_instance().API_SERVERS.X_RAPID_SECRET,
            'Content-Type': "application/json", 'Host': "gateway.eod-stock-api.site"}
