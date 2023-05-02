# EOD STOCK API - API--GATEWAY-VERSION 0.0.1

**api-gateway** is a Python-based API Gateway built using the FastAPI framework. It provides several key features to 
secure and manage your API endpoints.

## Features

### API key based authorization

API key based authorization ensures that only authorized clients can access your API endpoints. 
When a client sends a request to the API gateway, it checks the API key provided in the request headers and 
verifies it against a list of authorized API keys.

```python
def auth_and_rate_limit(func):
    # noinspection PyTypeChecker
    async def return_kwargs(kwargs):
        request: Request = kwargs.get('request')
        api_key = request.query_params.get('api_key')
        path = kwargs.get('path')
        return api_key, path

    async def rate_limiter(api_key):
        """
        **rate_limiter**
            this only rate limits clients by api keys,
            there is also a regional rate limiter and a global rate limit both created so that the gateway
            does not end up taking too much traffic and is able to recover from DDOS attacks easily.

        --> the rate_limiter has a side effect of also authorizing the client based on API Keys

        this method applies the actual rate_limiter per client basis"""
        # Rate Limiting Section
        async with apikeys_lock:
            api_keys_model_dict: dict[str, str | int] = api_keys_lookup(api_key)
            now = time.monotonic()
            duration: int = api_keys_model_dict.get('duration')
            limit: int = api_keys_model_dict.get('rate_limit')
            last_request_timestamp: float = api_keys_model_dict.get('last_request_timestamp')
            # Note that APiKeysModel must be updated with plan rate_limit
            if now - last_request_timestamp > duration:
                api_keys_model_dict['requests_count'] = 0
            if api_keys_model_dict['requests_count'] >= limit:
                time_left = last_request_timestamp + duration - now
                mess: str = f"EOD Stock API - Rate Limit Exceeded. Please wait {time_left:.0f} seconds before making " \
                            f"another request, or upgrade your plan to better take advantage of extra resources " \
                            f"available on better plans."

                rate_limit_dict = {'duration': duration, 'rate_limit': limit, 'time_left': f"{time_left:.0f}"}
                raise RateLimitExceeded(rate_limit=rate_limit_dict, status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                        detail=mess)
            # NOTE Updating number of requests and timestamp
            api_keys_model_dict['requests_count'] += 1
            # noinspection PyTypeChecker
            api_keys_model_dict['last_request_timestamp'] = now
            api_keys[api_key] = api_keys_model_dict

    @wraps(func)
    async def wrapper(*args, **kwargs):
        """main wrapper"""
        api_key, path = await return_kwargs(kwargs)

        path = f"/api/v1/{path}"
        api_key_found = api_key in api_keys
        if not api_key_found:
            await cache_api_keys_func()  # Update api_keys if the key is not found
            api_key_found = api_key in api_keys

        if not api_key_found:
            # user not authorized to access this routes
            mess = "EOD Stock API - Invalid API Key, or Cancelled API Key please subscribe to get a valid API Key"
            raise NotAuthorized(message=mess)

        # actual rate limiter
        await rate_limiter(api_key)

        # Authorization Section
        # Use asyncio.gather to run is_resource_authorized and monthly_credit_available concurrently
        is_authorized_task = asyncio.create_task(is_resource_authorized(path_param=path, api_key=api_key))
        monthly_credit_task = asyncio.create_task(monthly_credit_available(api_key=api_key))
        is_authorized, monthly_credit = await asyncio.gather(is_authorized_task, monthly_credit_task)

        if is_authorized and monthly_credit:
            return await func(*args, **kwargs)

        if not is_authorized:
            mess: str = "EOD Stock API - Request not Authorized, Either you are not subscribed to any plan or you " \
                        "need to upgrade your subscription"
            raise NotAuthorized(message=mess)

        if not monthly_credit:
            mess: str = f"EOD Stock API - Your Monthly plan request limit has been reached. " \
                        f"please upgrade your plan, to take advantage of our soft limits"
            raise NotAuthorized(message=mess)

    return wrapper

```

### Regional edge server based request throttling

The regional edge server based request throttling feature ensures that a client cannot overwhelm the API gateway 
with too many requests. 

The API gateway keeps track of the number of requests coming from each edge IP address and enforces a limit on the 
number of requests that can be made in a given time period. if the limit is exceeded the requests will be throttled 
this will not affect other clients making use of our services from regions where there is no huge traffic

```python
@app.middleware(middleware_type="http")
async def edge_request_throttle(request: Request, call_next):
    """
        Middleware will throttle requests if they are more than 100 requests per second
        per edge, other edge servers may be serviced just as before but the one server
        where higher traffic is coming from will be limited
    """
    # rate limit by Edge Server IP Address, this will have the effect of throttling entire regions if flooding requests
    # are mainly coming from such regions
    ip_address = await cf_firewall.get_edge_server_ip(headers=request.headers)
    if ip_address not in ip_rate_limits:
        # This will throttle the connection if there is too many requests coming from only one edge server
        ip_rate_limits[ip_address] = RateLimit()

    is_throttled = False
    if await ip_rate_limits[ip_address].is_limit_exceeded():
        await ip_rate_limits[ip_address].ip_throttle(edge_ip=ip_address, request=request)
        is_throttled = True
    # continue with the request
    # either the request was throttled and now proceeding or all is well
    app_logger.info(f"On Entry to : {request.url.path}")
    response = await call_next(request)

    # attaching a header showing throttling was in effect and proceeding
    if is_throttled:
        response.headers["X-Request-Throttled-Time"] = f"{ip_rate_limits[ip_address].throttle_duration} Seconds"
    return response

```

### API key based client request rate limiting

API key based client request rate limiting provides an additional layer of protection against DDoS attacks by limiting 
the number of requests a client can make in a given time period. 

The API Gateway checks the number of requests made by each client using their API key and enforces a limit on the 
number of requests that can be made in a given time period.


### Regex based request filtering

Regex based request filtering ensures that only whitelisted requests can reach the API gateway. The API gateway checks 
the request URL against a list of regular expressions and rejects any requests that do not match any of the 
regular expressions. The regular expressions matches pre configured url routes
```python
# dicts of Known Routes being serviced by the gateway example 
route_regexes = {
    "home": "^/$",
    "all_general_fundamentals": "^/api/v1/fundamental/general$",
    ...}
 
    def __init__(self):
        ...
        self.compiled_patterns = [re.compile(_regex) for _regex in route_regexes.values()]
        
    async def path_matches_known_route(self, path: str):
        """
        **path_matches_known_route**
            helps to filter out malicious paths based on regex matching
        parameters:
            path: this is the path parameter of the request being requested

        """
        # NOTE: that at this stage if this request is not a get then it has already been rejected
        # NOTE: this will return true if there is at least one route that matches with the requested path.
        # otherwise it will return false and block the request
        return any(pattern.match(path) for pattern in self.compiled_patterns)

```

### Resource based request authorization

Resource based request authorization allows you to control which API resources can be accessed by each client. 
The API gateway checks the API key or username provided in the request headers and verifies it against a 
list of authorized clients for the specific resource.

## Getting started

To get started with **api-gateway**, follow these steps:

1. Clone the repository:
https://github.com/MJ-API-Development/api-gateway

The API gateway should now be accessible at 
https://gateway.eod-stock-api.site 

## Contributing

If you want to contribute to **api-gateway**, please follow these steps:

- Fork the repository.
- Create a new branch for your feature or bug fix:
- Make your changes and commit them:
- Push your changes to your fork:
- Create a pull request to the main repository.


## Links
- [EOD Stock API - Intelligent Stock Market API](https://eod-stock-api.site)
- [PythonSDK - Intelligent Stock Market API](https://pypi.org/project/Intelligent-Stock-Market-API/)
- [Developers Blog - EOD Stock API](https://eod-stock-api.site/blog)
- [EOD STOCK API - Gateway Server](https://gateway.eod-stock-api.site)
- [EOD Stock API - Redoc Documentations](https://eod-stock-api.site/redoc)

## Community
- [Slack Channel](https://join.slack.com/t/eod-stock-apisite/shared_invite/zt-1uelcf229-c_6QAgWFNyVfXKZr1hYYoQ)
- [StackOverflow](https://stackoverflowteams.com/c/eod-stock-market-api)
- [Quora](https://eodstockmarketapi.quora.com/)

## License
**api-gateway** is licensed under the MIT License. See the `LICENSE` file for details. 
