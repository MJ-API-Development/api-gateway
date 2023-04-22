import asyncio
import time

from fastapi.requests import Request
from src.utils.my_logger import init_logger


class RateLimit:
    """
    **RateLimit**
         Used to Throttle My API into just over 100 requests per second
         This works because the API is being used over cloudflare so throttling
         requests to less than 100 per second for each edge server in cloudflare
         makes sense. should leave room enough to service other regions
    """
    def __init__(self, max_requests: int = 100, duration: int = 1):
        self.max_requests = max_requests
        self.duration_seconds = duration
        self.requests = []
        self.throttle_duration: int = 5
        self._logger = init_logger("global_throttle")

    async def is_limit_exceeded(self) -> bool:
        now = time.monotonic()
        # remove old requests from the list
        self.requests = [r for r in self.requests if r > now - self.duration_seconds]
        # check if limit is exceeded
        if len(self.requests) >= self.max_requests:
            return True
        self.requests.append(now)
        return False

    async def ip_throttle(self, edge_ip: str,  request: Request):
        mess = f"""
            Throttling Requests
                request from = {edge_ip}
                resource_path = {request.url.path}
                request_headers = {request.headers}
        """
        """sleeps for 5 seconds"""
        self._logger.warning(mess)
        await asyncio.sleep(self.throttle_duration)
        return


ip_rate_limits: dict[str, RateLimit] = {}
