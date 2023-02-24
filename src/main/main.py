import asyncio

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from numba import jit

from src.apikeys.keys import cache_api_keys
from src.config import config_instance
from src.ratelimit.limit import auth_and_rate_limit
from src.views_cache.cache import cached

description = """

**Stock Marketing & Financial News API**,

    provides end-of-day stock information for multiple exchanges around the world. 
    With this API, you can retrieve data for a specific stock at a given date, or for a range of dates. and also get access
    to companies fundamental data, financial statements, social media trending stocks by sentiment, and also the ability to create a summary of the Financial 
    News Related to a certain stock or company and its sentiment.

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


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )


@app.get("/test-error-handling")
async def test_error_handling():
    response = await _request("https://example.com/non-existent-url")
    return response.json()


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

# Prefetch endpoints
PREFETCH_ENDPOINTS = [
    '/api/v1/exchanges',
    '/api/v1/stocks']

@jit
async def prefetch_endpoints():
    while True:
        for api_server_url in api_server_urls:
            for endpoint in PREFETCH_ENDPOINTS:
                api_url = f'{api_server_url}{endpoint}'
                response = await _request(api_url)
        # Sleep for PREFETCH_INTERVAL seconds before running the loop again
        await asyncio.sleep(config_instance().PREFETCH_INTERVAL)


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

    # create an ijson parser for the response content
    # create response
    headers = {"Content-Type": "application/json"}
    content = response.json()
    status_code = response.status_code
    return JSONResponse(content=content, status_code=status_code, headers=headers)

    # data = response.json()
    # content = data
    # status_code = response.status_code
    # return JSONResponse(content=content, status_code=status_code, headers=headers)


# Use the connection pool limits in the AsyncClient
async_client = httpx.AsyncClient(http2=True)


@cached
@jit
async def _request(api_url: str):
    try:
        headers = await set_headers()
        response = await async_client.get(api_url, headers=headers)
        response.raise_for_status()
    except httpx.HTTPError as http_err:
        raise http_err
    except Exception as err:
        raise err
    return response


@cached
@jit
async def set_headers():
    return {'X-API-KEY': config_instance().API_SERVERS.X_API_KEY,
            'X-SECRET-TOKEN': config_instance().API_SERVERS.X_SECRET_TOKEN,
            'X-RapidAPI-Proxy-Secret': config_instance().API_SERVERS.X_RAPID_SECRET,
            'Content-Type': "application/json", 'Host': "gateway.eod-stock-api.site"}
