from src.main.main import api_server_urls
from src.prefetch.dynamic_urls import build_dynamic_urls
from src.requests import requester


async def prefetch_endpoints():
    for api_server_url in api_server_urls:
        for endpoint in build_dynamic_urls():
            api_url = f'{api_server_url}{endpoint}'
            response = await requester(api_url)
