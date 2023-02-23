import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.apikeys.keys import cache_api_keys
from src.ratelimit.limit import auth_and_rate_limit, RATE_LIMIT, RATE_LIMIT_DURATION
from src.config import config_instance

app = FastAPI()


# Use a background task to periodically update the `api_keys` dict
@app.on_event('startup')
async def startup_event():
    import asyncio

    async def update_api_keys_background_task():
        while True:
            cache_api_keys()
            await asyncio.sleep(60)

    asyncio.create_task(update_api_keys_background_task())


api_server_urls = [config_instance().API_SERVERS.MASTER_API_SERVER, config_instance().API_SERVERS.SLAVE_API_SERVER]
api_server_counter = 0


@app.api_route("/{path:path}", methods=["GET"])
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

    api_url = f'{api_server_url}/{path}'
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
