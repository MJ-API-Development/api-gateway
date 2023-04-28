import asyncio
import datetime
import hashlib
import hmac
import itertools
import time
from json.decoder import JSONDecodeError

import httpx
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import true
from starlette.responses import HTMLResponse, RedirectResponse

from src.authorize.authorize import auth_and_rate_limit, create_take_credit_args, process_credit_queue, NotAuthorized, \
    load_plans_by_api_keys, RateLimitExceeded
from src.cache.cache import redis_cache
from src.cloudflare_middleware import EODAPIFirewall
from src.config import config_instance
from src.database.apikeys.keys import cache_api_keys
from src.database.plans.init_plans import RateLimits
from src.make_request import async_client
from src.management_api.email.email import email_process
from src.management_api.routes import admin_app
from src.prefetch import prefetch_endpoints
from src.ratelimit import ip_rate_limits, RateLimit
from src.requests import requester, ServerMonitor
from src.utils.my_logger import init_logger
from src.utils.utils import is_development

cf_firewall = EODAPIFirewall()
# API Servers
# TODO NOTE will add more Server URLS Later
#  TODO just use a server list straight from config
api_server_urls = config_instance().API_SERVERS.SERVERS_LIST.split(',')
api_server_counter = 0

# used to logging debug information for the application
app_logger = init_logger("eod_stock_api_gateway")

description = """
**Stock Marketing & Financial News API**,

    provides end-of-day stock information for multiple exchanges around the world. 
    With this API, you can retrieve data for a specific stock at a given date, or for a range of dates. and also get access
    to companies fundamental data, financial statements, social media trending stocks by sentiment, and also the ability to create a summary of the Financial 
    News Related to a certain stock or company and its sentiment.
"""

app = FastAPI(
    title="EOD-STOCK-API - API GATEWAY",
    description=description,
    version="1.0.0",
    terms_of_service="https://eod-stock-api.site/terms",
    contact={
        "name": "EOD-STOCK-API",
        "url": "https://eod-stock-api.site/contact",
        "email": "info@eod-stock-api.site"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    docs_url=None,
    openapi_url=None,
    redoc_url=None
)

app.mount("/static", StaticFiles(directory="src/main/static"), name="static")


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # ERROR HANDLERS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

@app.exception_handler(RateLimitExceeded)
async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """
    **rate_limit_error_handler**
        will handle Rate Limits Exceeded Error
    :param request:
    :param exc:
    :return:
    """
    app_logger.error(msg=f"""
    Rate Limit Error

    Debug Information
        request_url: {request.url}
        request_method: {request.method}

        error_detail: {exc.detail}
        rate_limit: {exc.rate_limit}
        status_code: {exc.status_code}    
    """)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'message': exc.detail,
            'rate_limit': exc.rate_limit
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP Error Handler Will display HTTP Errors in JSON Format to the client"""
    app_logger.info(msg=f"""
    HTTP Exception Occurred 

    Debug Information
        request_url: {request.url}
        request_method: {request.method}

        error_detail: {exc.detail}
        status_code: {exc.status_code}
    """)

    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail})


@app.exception_handler(NotAuthorized)
async def handle_not_authorized(request, exc):
    app_logger.info(f"""
        Not Authorized Error

        Debug Information
        request_url: {request.url}
        request_method: {request.method}
        error_detail: {exc.message}
        status_code: {exc.status_code}

    """)
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(JSONDecodeError)
async def handle_json_decode_error(request, exc):
    app_logger.info(f"""
    Error Decoding JSON    
        Debug Information
        request_url: {request.url}
        request_method: {request.method}
        error_detail: "error decoding JSON"
        status_code: {exc.status_code}    
    """)
    await delete_resource_from_cache(request)

    message: str = "Oopsie- Server Error, Hopefully our engineers will resolve it soon"
    return JSONResponse(status_code=exc.status_code, content=message)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # MIDDLE WARES
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """adding security headers"""

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # # TODO find a normal way to resolve this
    if not request.url.path.startswith("/redoc") and not request.url.path.startswith("/_admin/redoc"):
        response.headers[
            "Content-Security-Policy"] = "default-src 'none'; script-src 'self' https://cdn.redoc.ly; connect-src 'self'; img-src 'self'; style-src 'self'"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


if is_development(config_instance=config_instance):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["gateway.eod-stock-api.site", "localhost", "127.0.0.1"])
else:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["gateway.eod-stock-api.site"])

# Rate Limit per IP Must Always Match The Rate Limit of the Highest Plan Allowed
rate_limit, _, duration = RateLimits().ENTERPRISE


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


@app.middleware(middleware_type="http")
async def check_ip(request: Request, call_next):
    """
        determines if call originate from cloudflare
    :param request:
    :param call_next:
    :return:
    """
    # THE Cloudflare IP Address is a client in this case as its the one sending the requests
    edge_ip: str = await cf_firewall.get_edge_server_ip(headers=request.headers)
    app_logger.info(f"Client IP Address : {edge_ip}")

    if edge_ip and await cf_firewall.check_ip_range(ip=edge_ip):
        response = await call_next(request)
    elif is_development(config_instance=config_instance):
        response = await call_next(request)
    else:
        return JSONResponse(
            content={
                "message": "Access denied, Bad Gateway Address we can only process request from our gateway server",
                "gateway": "https://gateway.eod-stock-api.site"},
            status_code=403)

    return response


# Create a middleware function that checks the IP address of incoming requests and only allows requests from the
# Cloudflare IP ranges. Here's an example of how you could do this:
@app.middleware(middleware_type="http")
async def validate_request_middleware(request, call_next):
    """
        checks if the request comes from cloudflare through a token
        also check if the path is going to a good path / route if not it blocks the request
    :param request:
    :param call_next:
    :return:
    """

    # This code will be executed for each incoming request
    # before it is processed by the route handlers.
    # You can modify the request here, or perform any other
    # pre-processing that you need.
    # allowedPaths = ["/", "/api/", "/redoc", "/docs", "/_admin/"]

    async def compare_tokens():
        """will check headers to see if the request comes from cloudflare"""
        _cf_secret_token = request.headers.get('X-SECRET-TOKEN')
        _cloudflare_token = config_instance().CLOUDFLARE_SETTINGS.CLOUDFLARE_SECRET_KEY
        app_logger.info(f"Request Headers : {request.headers}")
        if _cf_secret_token is None:
            return False

        hash_func = hashlib.sha256  # choose a hash function
        secret_key = config_instance().SECRET_KEY
        digest1 = hmac.new(secret_key.encode(), _cf_secret_token.encode(), hash_func).digest()
        digest2 = hmac.new(secret_key.encode(), _cloudflare_token.encode(), hash_func).digest()
        return hmac.compare_digest(digest1, digest2)

    path = str(request.url.path)
    _url = str(request.url)
    start_time = time.monotonic()

    if await cf_firewall.is_request_malicious(headers=request.headers, url=request.url, body=str(request.body)):
        """
            If we are here then there is something wrong with the request
        """
        mess: dict[str, str] = {
            "message": "Request Contains Suspicious patterns cannot continue"}
        response = JSONResponse(content=mess, status_code=404)
        return response

    if path.startswith("/_admin") or path.startswith("/redoc") or path.startswith("/docs") or path.startswith(
            "/static"):
        app_logger.info("starts with admin going in ")
        response = await call_next(request)

    elif path in ["/open-api", "/"]:
        """letting through specific URLS for Documentation"""
        app_logger.info(f"Routing to Documentations : {path}")
        response = await call_next(request)

    elif is_development(config_instance=config_instance):
        response = await call_next(request)

    elif not await compare_tokens():
        mess: dict[str, str] = {
            "message": "Request Is not valid Bad Token please ensure you are routing this request through our gateway"}
        response = JSONResponse(content=mess, status_code=404)

    # Going to API
    elif await cf_firewall.path_matches_known_route(path=path):
        response = await call_next(request)
    else:
        app_logger.warning(msg=f"""
            Potentially Bad Route Being Accessed
                    request.url = {request.url}

                    request.method = {request.method}

                    request.headers = {request.headers}

                    request_time = {datetime.datetime.now().isoformat(sep="-")}
        """)
        # raise NotAuthorized(message="Route Not Allowed, if you think this maybe an error please contact admin")
        response = JSONResponse(content="Request Does not Match Any Known Route", status_code=404)

    # This code will be executed for each outgoing response
    # before it is sent back to the client.
    # You can modify the response here, or perform any other
    # post-processing that you need.
    # _out_signature = await cf_firewall.create_signature(response=response, secret=_secret)
    # response.headers.update({'X-Signature': _out_signature})
    end_time = time.monotonic()
    app_logger.info(f"Elapsed Time Validate Request : {end_time - start_time}")
    app_logger.info("Cleared Request Validation")
    return response


#######################################################################################################################


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # STARTUP EVENTS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
remote_servers = ServerMonitor()


# On Start Up Run the following Tasks
@app.on_event('startup')
async def startup_event():
    async def setup_cf_firewall():
        app_logger.info("Application Setup")
        ipv4_cdrs, ipv6_cdrs = await cf_firewall.get_ip_ranges()
        cf_firewall.ip_ranges = list(itertools.chain(*[ipv4_cdrs, ipv6_cdrs]))

        app_logger.info(f"CF Firewall Added {len(ipv4_cdrs)} IP-V4 & {len(ipv6_cdrs)} IP-V6 Addresses")
        # This will restore a list of known Bad IP Addresses
        await cf_firewall.restore_bad_addresses_from_redis()

    async def update_api_keys_background_task():
        while True:
            # Caching API Keys , plans and Subscriptions
            total_apikeys: int = await cache_api_keys()
            app_logger.info(f"Cache Prefetched {total_apikeys} apikeys")
            await load_plans_by_api_keys()
            # wait for 5 minutes then update API Keys records
            await asyncio.sleep(60 * 15)

    # noinspection PyUnusedLocal
    async def prefetch():
        """
            Method to Prefetch Common Routes for faster Execution
        :return:
        """
        while True:
            if not is_development(config_instance=config_instance):
                app_logger.info(f"Started Pre Fetching Requests")
                total_prefetched = await prefetch_endpoints()
                app_logger.info(f"Cache Pre Fetched {total_prefetched} endpoints")

            #  wait for one hour 30 minutes then prefetch urls again
            await asyncio.sleep(60 * 60 * 3)

    async def backup_cf_firewall_data():
        while True:
            total_bad_addresses = await cf_firewall.save_bad_addresses_to_redis()
            app_logger.info(f"CF Firewall Backed Up {total_bad_addresses} Bad Addresses")
            # Everyday
            # Runs every 24 hours in order to backup bad addresses list
            await asyncio.sleep(60 * 60 * 24)

    async def clean_up_memcache():
        while True:
            # This cleans up the cache every 30 minutes
            total_cleaned = await redis_cache.memcache_ttl_cleaner()
            app_logger.info(f"Cleaned Up {total_cleaned} Expired Mem Cache Values")
            await asyncio.sleep(delay=60 * 30)

    async def monitor_servers():
        """will prioritize servers which are responsive and also available"""
        while True:
            await remote_servers.sort_api_servers_by_health()
            await asyncio.sleep(delay=60 * 5)

    asyncio.create_task(setup_cf_firewall())
    asyncio.create_task(backup_cf_firewall_data())
    asyncio.create_task(update_api_keys_background_task())
    # asyncio.create_task(prefetch())
    asyncio.create_task(process_credit_queue())
    asyncio.create_task(email_process.process_message_queues())
    asyncio.create_task(clean_up_memcache())
    asyncio.create_task(monitor_servers())


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # ADMIN APP
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# TODO ensure that the admin APP is running on the Admin Sub Domain Meaning this should Change
# TODO Also the Admin APP must be removed from the gateway it will just slow down the gateway


# TODO Admin Application Mounting Point should eventually Move this
# To its own separate Application
app.mount(path="/_admin", app=admin_app, name="admin_app")


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # API GATEWAY
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

@app.get("/api/v1/{path:path}", include_in_schema=False)
@auth_and_rate_limit
async def v1_gateway(request: Request, path: str):
    """
    NOTE: In order for the gateway server to work properly it needs at least 2 GIG or RAM
        master router
    :param request:
    :param path:
    :return:
    """

    api_key: dict = request.query_params.get('api_key')
    _path = f"/api/v1/{path}"
    await create_take_credit_args(api_key=api_key, path=_path)

    api_urls = [f'{api_server_url}/api/v1/{path}' for api_server_url in remote_servers.healthy_server_urls]

    # Will Take at least six second on the cache if it finds nothing will return None
    # need an improved get timeout for the articles
    tasks = [redis_cache.get(key=api_url, timeout=60 * 5) for api_url in api_urls]
    cached_responses = await asyncio.gather(*tasks)

    for i, response in enumerate(cached_responses):
        if response and response.get('payload'):
            app_logger.info(msg=f"Found cached response from {api_urls[i]}")
            return JSONResponse(content=response, status_code=200, headers={"Content-Type": "application/json"})

    app_logger.info(msg="All cached responses not found- Must Be a Slow Day")
    for api_url in remote_servers.healthy_server_urls:
        try:
            # 5 minutes timeout on resource fetching from backend - some resources may take very long
            response = await requester(api_url=api_url, timeout=9600)
            if response and response.get("status", False) and response.get('payload'):
                # NOTE, Cache is being set to a ttl of one hour here
                await redis_cache.set(key=api_url, value=response, ttl=60 * 60)
                return JSONResponse(content=response, status_code=200, headers={"Content-Type": "application/json"})
        except httpx.HTTPError as http_err:
            app_logger.info(msg=f"Errors when making requests : {str(http_err)}")

    mess = "All API Servers failed to respond - Or there is no Data for the requested resource and parameters"
    app_logger.warning(msg=mess)
    _time = datetime.datetime.now().isoformat(sep="-")

    # Note: Sending Message to developers containing the details of the request of which there was no data at all
    _args = dict(message_type="resource_not_found", request=request, api_key=api_key)
    await email_process.send_message_to_devs(**_args)

    return JSONResponse(content={"status": False, "message": mess}, status_code=404,
                        headers={"Content-Type": "application/json"})


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # Documentations Routes
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# noinspection PyUnusedLocal
@app.get("/open-api", include_in_schema=False)
async def open_api(request: Request):
    """
    **open_api**
        will return a json open api specification for the main API
    :param request:
    :return:
    """
    spec_url = "https://raw.githubusercontent.com/MJ-API-Development/open-api-spec/main/open-api.json"
    response = await redis_cache.get(key=spec_url, timeout=1)
    if response is None:
        data = await async_client.get(url=spec_url, timeout=60 * 5)
        if data:
            response = data.json()
            await redis_cache.set(key=spec_url, value=response, ttl=60 * 60)

    return JSONResponse(content=response, status_code=200, headers={"Content-Type": "application/json"})


# noinspection PyUnusedLocal
@app.get("/", include_in_schema=True)
async def home_route(request: Request):
    """
    **home_route**
        redirects to documentations
    :return:
    """
    return RedirectResponse(url="/redoc", status_code=301)


# noinspection PyUnusedLocal
@app.get("/redoc", include_in_schema=False, response_class=HTMLResponse)
async def redoc_html(request: Request):
    return get_redoc_html(
        openapi_url='https://gateway.eod-stock-api.site/open-api',
        title=app.title + " - ReDoc",
        redoc_js_url="https://gateway.eod-stock-api.site/static/redoc.standalone.js",
        with_google_fonts=true
    )


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # CACHE MANAGEMENT UTILS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

async def create_resource_keys(request: Request) -> list[str]:
    """
    **create_resource_keys**
        create resource keys for urls
    :param request:
    :return:
    """
    return [f"{b_server}{request.url.path}" for b_server in api_server_urls]


async def delete_resource_from_cache(request: Request):
    """
    **delete_resource_from_cache**
        This will delete any resource associated with a request from cache if such a
        resource is causing errors such as JSON Decode Errors
    :return:
    """
    try:
        resource_keys: list[str] = await create_resource_keys(request)
        for resource_key in resource_keys:
            await redis_cache.delete_key(key=resource_key)
    except Exception as e:
        app_logger.error(msg=str(e))


async def check_all_services():
    """
    **heck_all_services**
        compile a full list of services and show if they are available
    :return:
    """
    ping_master = requests.get('https://stock-eod-api.site/_ah/warmup')
    master = "Offline"

    if ping_master.status_code == 200:
        master = "online"

    return {
        'Gateway': 'Online',
        'API_Master': master,
        'API_Slave': 'Online'
    }


# noinspection PyUnusedLocal
@app.get("/_ah/warmup", include_in_schema=False)
async def status_check(request: Request):
    _payload = await check_all_services()
    response = dict(payload=_payload)
    return JSONResponse(content=response, status_code=200, headers={"Content-Type": "application/json"})
