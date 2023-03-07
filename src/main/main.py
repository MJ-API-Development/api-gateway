import asyncio
import datetime
import itertools
from json.decoder import JSONDecodeError

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.authorize.authorize import auth_and_rate_limit, create_take_credit_args, process_credit_queue, NotAuthorized, \
    load_plans_by_api_keys, RateLimitExceeded
from src.cache.cache import redis_cache
from src.cloudflare_middleware import CloudFlareFirewall
from src.config import config_instance
from src.database.apikeys.keys import cache_api_keys
from src.email.email import email_process
from src.management_api.routes import admin_app
from src.prefetch import prefetch_endpoints
from src.requests import requester
from src.utils.my_logger import init_logger

cf_firewall = CloudFlareFirewall()
# API Servers
api_server_urls = [config_instance().API_SERVERS.MASTER_API_SERVER, config_instance().API_SERVERS.SLAVE_API_SERVER]
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
    title="EOD-STOCK-API - GATEWAY",
    description=description,
    version="1.0.0",
    terms_of_service="https://www.eod-stock-api.site/terms",
    contact={
        "name": "EOD-STOCK-API",
        "url": "/contact",
        "email": "info@eod-stock-api.site"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"]
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """

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
    app_logger.error(msg=f"""
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
    app_logger.error(f"""
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
    app_logger.error(f"""
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


# Create a middleware function that checks the IP address of incoming requests and only allows requests from the
# Cloudflare IP ranges. Here's an example of how you could do this:
@app.middleware("http")
async def validate_request_middleware(request: Request, call_next):
    """

    :param request:
    :param call_next:
    :return:
    """
    # This code will be executed for each incoming request
    # before it is processed by the route handlers.
    # You can modify the request here, or perform any other
    # pre-processing that you need.

    signature = request.headers.get('X-Signature')
    _secret = config_instance().SECRET_KEY
    _url: str = str(request.url)
    # TODO ensure that the admin APP is running on the Admin Sub Domain Meaning this should Change
    # TODO Also the Admin APP must be removed from the gateway it will just slow down the gateway
    if signature is None and _url.startswith("https://gateway.eod-stock-api.site/_admin"):
        response = await call_next(request)

    elif await cf_firewall.path_matches_known_route(request=request):
            response  = await call_next(request)
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
    return response


@app.middleware("http")
async def check_ip(request: Request, call_next):
    """
        determines if call originate from cloudflare
    :param request:
    :param call_next:
    :return:
    """
    # TODO consider adding header checks
    ip = request.client.host
    if not await cf_firewall.check_ip_range(ip=ip):
        return JSONResponse(
            content={"message": "Access denied, Suspicious Activity, Use a Proper Gateway to access our resources"},
            status_code=403)

    return await call_next(request)


app.add_middleware(TrustedHostMiddleware)




# TODO Admin Application Mounting Point should eventually Move this
# To its own separate Application
app.mount(path="/_admin", app=admin_app)


# On Start Up Run the following Tasks
@app.on_event('startup')
async def startup_event():
    async def setup_cf_firewall():
        app_logger.info("Setting Up CF Firewall...")
        ipv4_cdrs, ipv6_cdrs = await cf_firewall.get_ip_ranges()
        cf_firewall.ip_ranges = list(itertools.chain(*[ipv4_cdrs, ipv6_cdrs]))
        await cf_firewall.restore_addresses_from_redis()
        app_logger.info("Done Setting Up CF Firewall...")

    async def update_api_keys_background_task():
        while True:
            app_logger.info("Started Pre Fetching API Keys")
            # Caching API Keys , plans and Subscriptions
            await cache_api_keys()
            await load_plans_by_api_keys()
            app_logger.info("Done Pre Fetching API Keys")

            # wait for 15 minutes then update API Keys records
            await asyncio.sleep(60 * 15)

    async def prefetch():
        """
        Method to Prefetch Common Routes for faster Execution
        :return:
        """
        while True:
            app_logger.info("Started Pre Fetching End Points")
            await prefetch_endpoints()
            app_logger.info("Done Pre Fetching End Points")

            #  wait for one hour 30 minutes then prefetch urls again
            await asyncio.sleep(60 * 60 * 1.5)

    async def backup_cf_firewall_data():
        while True:
            await cf_firewall.save_bad_addresses_to_redis()
            # Everyday
            await asyncio.sleep(60 * 60 * 24)
            app_logger.info("CF Firewall Bad Addresses Backed Up")

    async def clean_up_memcache():
        while True:
            await redis_cache.memcache_ttl_cleaner()
            await asyncio.sleep(delay=60*10)
            app_logger.info("Cleaning Up Expired Mem Cache Items")

    asyncio.create_task(setup_cf_firewall())
    asyncio.create_task(backup_cf_firewall_data())
    asyncio.create_task(update_api_keys_background_task())
    asyncio.create_task(prefetch())
    asyncio.create_task(process_credit_queue())
    asyncio.create_task(email_process.process_message_queues())
    asyncio.create_task(clean_up_memcache())


@app.api_route("/api/v1/{path:path}", methods=["GET"], include_in_schema=True)
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

    api_urls = [f'{api_server_url}/api/v1/{path}' for api_server_url in api_server_urls]

    # Will Take at least one second on the cache if it finds nothing will return None
    tasks = [redis_cache.get(key=api_url, timeout=1) for api_url in api_urls]
    cached_responses = await asyncio.gather(*tasks)

    for i, response in enumerate(cached_responses):
        if response is not None:
            app_logger.info(msg=f"Found cached response from {api_urls[i]}")
            return JSONResponse(content=response, status_code=200, headers={"Content-Type": "application/json"})

    app_logger.info(msg="All cached responses not found- Must Be a Slow Day")

    # 5 minute timeout on resource fetching from backend - some resources may take very long
    tasks = [requester(api_url=api_url, timeout=5*60) for api_url in api_urls]
    responses = await asyncio.gather(*tasks)

    for i, response in enumerate(responses):
        if response and response.get("status"):
            api_url = api_urls[i]
            # NOTE, Cache is being set to a ttl of one hour here
            await redis_cache.set(key=api_url, value=response, ttl=60 * 60)
            app_logger.info(msg=f"Server Responded for this Resource {api_url}")
            return JSONResponse(content=response, status_code=200, headers={"Content-Type": "application/json"})
        else:
            # The reason for this algorithm is because sometimes the cron server is busy this way no matter
            # what happens a response is returned
            app_logger.warning(msg=f"""
            Server Failed To Respond
                Original Request URL : {api_urls[i]}
                Actual Response : Check Requester Debug Output          
            """)

    app_logger.fatal(msg="All API Servers failed to respond")
    # TODO - send Notifications to developers that the API Servers are down
    _time = datetime.datetime.now().isoformat(sep="-")

    # TODO - create Dev Message Types - Like Fatal Errors, and etc also create Priority Levels
    _args = dict(message_type="resource_not_found", request=request, api_key=api_key)
    await email_process.send_message_to_devs(**_args)
    return JSONResponse(content={"status": False, "message": "All API servers failed to respond"}, status_code=404,
                        headers={"Content-Type": "application/json"})


async def create_resource_keys(request: Request) -> list[str]:
    """
        create resource keys for urls
    :param request:
    :return:
    """
    return [f"{b_server}{request.url.path}" for b_server in api_server_urls]


async def delete_resource_from_cache(request: Request):
    """
        This will delete any resource associated with a request from cache if such a
        resource is causing errors such as JSON Decode Errors
    :return:
    """
    try:
        resource_keys = await create_resource_keys(request)
        for resource_key in resource_keys:
            await redis_cache.delete_key(key=resource_key)
    except Exception as e:
        app_logger.error(msg=str(e))
