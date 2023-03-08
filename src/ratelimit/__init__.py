from datetime import datetime
import time

ip_rate_limits = {}

class RateLimit:
    """
    RateLimit Class is used to keep track of the rate limits for each IP Address
    """
    def __init__(self, max_requests: int, duration: int):
        self.max_requests = max_requests
        self.duration = duration
        self.requests = []

    def is_limit_exceeded(self) -> bool:
        now = datetime.datetime.now()
        # remove old requests from the list
        self.requests = [r for r in self.requests if r > now - datetime.timedelta(seconds=self.duration)]
        # check if limit is exceeded
        if len(self.requests) >= self.max_requests:
            return True
        self.requests.append(now)
        return False
