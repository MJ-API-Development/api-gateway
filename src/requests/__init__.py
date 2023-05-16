import asyncio
import time

import httpx
from src.config import config_instance
from src.utils.my_logger import init_logger

# Use the connection pool limits in the AsyncClient
request_logger = init_logger("requester_logger")
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

        _response = f"""
            BACKEND SERVERS ACTUAL RESPONSES
    
            response_headers: {response.headers} 
    
            response_code: {response.status_code}
    
            response_text: {response.text}
        """
        if response.status_code not in [200, 201]:
            # only print log messages if request is not successfully
            request_logger.info(_response)

        response.raise_for_status()

    except httpx.HTTPError as http_err:
        raise http_err
    except Exception as err:
        raise err

    return response.json() if response.headers.get('Content-Type') == "application/json" else None


class ServerMonitor:

    def __init__(self):
        # 900 milliseconds
        self.response_time_thresh_hold: int = 900
        self.healthy_server_urls: list[str] = config_instance().API_SERVERS.SERVERS_LIST.split(",")
        # Define the health check endpoint for each server
        self._server_monitor_endpoint = '/_ah/warmup'

    # Define a function to check the health of each server
    async def check_health(self, api_url: str) -> tuple[str, bool]:
        # Send a GET request to the health check endpoint
        health_check_url = f"{api_url}{self._server_monitor_endpoint}"
        request_logger.info(f"Server Health Probe: {health_check_url}")
        try:
            response = await async_client.get(url=health_check_url)
            if response.status_code == 200:
                request_logger.info(f"server still healthy : {api_url}")
                return api_url, True
            else:
                request_logger.info(f"server not  healthy : {api_url}")
                request_logger.info(f"Response : {response.text}")
                return api_url, False

        except (ConnectionError, TimeoutError):
            return api_url, False
        except httpx.HTTPError:
            return api_url, False

    # Sort the healthy servers by their response time
    async def measure_response_time(self, api_url: str) -> tuple[str, float | None]:
        try:
            check_url: str = f"{api_url}{self._server_monitor_endpoint}"
            request_logger.info(f"Server Health Probe: {check_url}")
            start_time = time.perf_counter()
            response = await async_client.get(url=check_url)
            if response.status_code == 200:
                elapsed_time = int((time.perf_counter() - start_time) * 1000)
                request_logger.info(f"server : {api_url} latency : {elapsed_time}")
                return api_url, elapsed_time
            else:
                request_logger.info(f"server : {api_url} Not healthy")
                request_logger.info(f"Response : {response.text}")
                return api_url, None

        except (ConnectionError, TimeoutError):
            return api_url, None
        except httpx.HTTPError:
            return api_url, None

    async def sort_api_servers_by_health(self) -> None:
        # Check the health of each server asynchronously
        tasks = [self.check_health(api_url) for api_url in config_instance().API_SERVERS.SERVERS_LIST.split(",")]
        health_results = await asyncio.gather(*tasks)

        # Filter out the unhealthy servers
        healthy_api_urls = [api_url for api_url, is_healthy in health_results if is_healthy]

        tasks = [self.measure_response_time(api_url) for api_url in healthy_api_urls]
        response_time_results = await asyncio.gather(*tasks)
        sorted_response_times = sorted(response_time_results, key=lambda x: x[1])
        within_threshold = [api_url for api_url, response_time in sorted_response_times if response_time < self.response_time_thresh_hold]
        self.healthy_server_urls = within_threshold if within_threshold else [config_instance().API_SERVERS.SLAVE_API_SERVER]
