import asyncio
import datetime
import time


class RateLimit:
    """
    RateLimit Class is used to keep track of the rate limits for each IP Address
    """
    def __init__(self, max_requests: int = 100, duration: int = 1):
        self.max_requests = max_requests
        self.duration = duration
        self.requests = []

    async def is_limit_exceeded(self) -> bool:
        now = time.monotonic()

        # remove old requests from the list
        self.requests = [r for r in self.requests if r > now - datetime.timedelta(seconds=self.duration)]
        # check if limit is exceeded
        if len(self.requests) >= self.max_requests:
            return True
        self.requests.append(now)
        return False

    @staticmethod
    async def ip_throttle():
        """sleeps for 5 seconds"""
        return await asyncio.sleep(5)


ip_rate_limits: dict[str, RateLimit] = {}
