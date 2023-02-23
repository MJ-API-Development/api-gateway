import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.apikeys.keys import cache_api_keys
from src.ratelimit.limit import auth_and_rate_limit, RATE_LIMIT, RATE_LIMIT_DURATION
from src.config import config_instance

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
    allow_credentials=True,
    allow_methods=["*"],
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
            await asyncio.sleep(60*3)

    asyncio.create_task(update_api_keys_background_task())


api_server_urls = [config_instance().API_SERVERS.MASTER_API_SERVER, config_instance().API_SERVERS.SLAVE_API_SERVER]
api_server_counter = 0


@app.api_route("/api/v1/{path:path}", methods=["GET"])
@auth_and_rate_limit()
async def reroute_to_api_endpoint(request: Request, path: str, api_key: str):
    """
        master router
    :param request:
    :param path:
    :param api_key:
    :return:
    """
    global api_server_counter

    api_server_url = api_server_urls[api_server_counter]
    api_server_counter = (api_server_counter + 1) % len(api_server_urls)

    api_url = f'{api_server_url}/api/v1/{path}'

    async with httpx.AsyncClient() as client:
        headers = dict(request.headers)

        headers['X-API-KEY'] = config_instance().API_SERVERS.X_API_KEY
        headers['X-SECRET-TOKEN'] = config_instance().API_SERVERS.SECRET_TOKEN
        headers['X-RapidAPI-Proxy-Secret'] = config_instance().X_RAPID_SECRET

        response = await client.request(method=request.method, url=api_url, headers=headers,
                                        content=await request.body())
        content = response.content
        status_code = response.status_code
        headers = response.headers.items()
    return JSONResponse(content=content, status_code=status_code, headers=headers)
