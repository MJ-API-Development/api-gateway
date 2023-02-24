import asyncio


class ServiceUnavailableError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.status_code = 503


class CircuitBreaker:
    def __init__(self, threshold, timeout):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.state = 'closed'
        self.timer = None

    async def execute(self, func, *args, **kwargs):
        if self.state == 'open':
            try:
                result = await func(*args, **kwargs)
                self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                if self.failures >= self.threshold:
                    self.state = 'closed'
                    self.timer = asyncio.get_event_loop().call_later(self.timeout, self._set_half_open)
                raise ServiceUnavailableError(message="Reason Service Raised an Exception See Logs for Details")
        elif self.state == 'closed':
            raise ServiceUnavailableError(message="Service is not available at the moment")
        elif self.state == 'half-open':
            try:
                result = await func(*args, **kwargs)
                self.failures = 0
                self.state = 'open'
                return result
            except Exception as e:
                self.failures += 1
                if self.failures >= self.threshold:
                    self.state = 'closed'
                    self.timer = asyncio.get_event_loop().call_later(self.timeout, self._set_half_open)
                raise ServiceUnavailableError(message="Reason Service Raised an Exception See Logs for details")

    def _set_half_open(self):
        self.state = 'half-open'
        self.failures = 0
        self.timer = None
