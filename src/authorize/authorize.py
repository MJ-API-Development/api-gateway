import asyncio
import time
from functools import wraps

from fastapi import HTTPException, Request
from starlette import status

from src.authorize.resources import get_resource_name, resource_name_request_size
from src.cache.cache import redis_cache, redis_cached_ttl
from src.database.apikeys.keys import api_keys, cache_api_keys, ApiKeyModel, apikeys_lock
from src.database.database_sessions import sessions
from src.database.plans.plans import Subscriptions, Plans, PlanType
from src.utils.my_logger import init_logger

lock = asyncio.Lock()

api_keys_lookup = api_keys.get
cache_api_keys_func = cache_api_keys

take_credit_queue = []

ONE_DAY: int = 60 * 60 * 24
auth_logger = init_logger("auth-logger")

# Define cache keys
API_KEYS_TO_PLANS_KEY = "api_keys_to_plans"
API_KEYS_TO_SUBSCRIPTIONS_KEY = "api_keys_to_subscriptions"


class NotAuthorized(Exception):
    """Custom NotAuthorized Class"""

    def __init__(self, message):
        super().__init__(message)
        self.status_code = 401
        self.message = message


async def get_plans_dict(api_key: str):
    # Retrieve plans dict from Redis
    return await redis_cache.get(key=f"{API_KEYS_TO_PLANS_KEY}:{api_key}")
    # Convert Redis byte strings to regular strings and return
    # return {key.decode(): value.decode() for key, value in plans_dict.items()}


async def add_to_api_keys_to_plans_cache(api_key: str, plans_dict: dict):
    # Convert keys and values to byte strings for Redis
    # plans_dict_redis = {key.encode(): str(value).encode() for key, value in plans_dict.items()}
    # Set Redis hash
    await redis_cache.set(key=f"{API_KEYS_TO_PLANS_KEY}:{api_key}", value=plans_dict)


async def get_subscriptions_dict(api_key: str):
    # Retrieve subscriptions dict from Redis
    return await redis_cache.get(key=f"{API_KEYS_TO_SUBSCRIPTIONS_KEY}:{api_key}")
    # Convert Redis byte strings to regular strings and return
    # return {key.decode(): value.decode() for key, value in subscriptions_dict.items()}


async def add_to_api_keys_to_subscriptions_cache(api_key: str, subscriptions_dict: dict):
    # Convert keys and values to byte strings for Redis
    # subscriptions_dict_redis = {key.encode(): str(value).encode() for key, value in subscriptions_dict.items()}
    # Set Redis hash
    await redis_cache.set(key=f"{API_KEYS_TO_SUBSCRIPTIONS_KEY}:{api_key}", value=subscriptions_dict)


class RateLimitExceeded(HTTPException):
    def __init__(self, rate_limit: dict[str, str | int], detail: str, status_code: int):
        super().__init__(detail=detail, status_code=status_code)
        self.rate_limit = rate_limit


async def load_plans_by_api_keys() -> None:
    with next(sessions) as session:
        for api_key in api_keys:
            client_api_model: ApiKeyModel = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
            subscription_instance: Subscriptions = client_api_model.subscription
            if not subscription_instance:
                return False
            plan_instance: Plans = await Plans.get_plan_by_plan_id(plan_id=subscription_instance.plan_id,
                                                                   session=session)
            await add_to_api_keys_to_plans_cache(api_key=api_key, plans_dict=plan_instance.to_dict())
            await add_to_api_keys_to_subscriptions_cache(api_key=api_key,
                                                         subscriptions_dict=subscription_instance.to_dict())


@redis_cached_ttl(ttl=ONE_DAY)
async def is_resource_authorized(path_param: str, api_key: str) -> bool:
    """
        given a url and api_key check if the user can access the resource
        associated with the path parameter,
        can access means the plan the client is subscribed to has access to resource
        and also the client is fully paid up on the plan
    :param path_param:
    :param api_key:
    :return: True if Authorized
    """
    with next(sessions) as session:
        client_api_model: ApiKeyModel = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
        if client_api_model is None:
            # Note: it can happen that apikey has changed since the last update
            return False

        subscription: Subscriptions = client_api_model.subscription

        if not subscription:
            # TODO very important to trigger an email here indicating the user has not yet paid for services
            return False
        is_active = await subscription.is_active(session=session)

        resource_name = await get_resource_name(path=path_param)
        can_access_resource = await subscription.can_access_resource(resource_name=resource_name, session=session)
    return is_active and can_access_resource


async def monthly_credit_available(api_key: str) -> bool:
    """
        **monthly_plan_limit**
            Check the subscribed plan check the monthly plan limit
            check if there are still requests left
    :param api_key: used to identify the user plan
    :return: True if credit is available
    """
    # Need to speed this function up considerably
    plan_dict = await get_plans_dict(api_key=api_key)
    subscription_dict = await get_subscriptions_dict(api_key=api_key)

    if plan_dict.get("plan_limit") <= subscription_dict.get("api_requests_balance"):
        # if hard_limit is true then monthly credit is not available
        return not plan_dict.get("plan_limit_type") == PlanType.hard_limit
    return True


async def create_take_credit_args(api_key: str, path: str):
    """
    **take_credit**
        will add the arguments to the processing queue for the take_credit method
    :param path:
    :param api_key:
    :return: None
    """
    async with lock:
        take_credit_queue.append(dict(api_key=api_key, path=path))


async def take_credit_method(api_key: str, path: str):
    """
        this method will update the request balance on the in memory
        dict, and then also update the database model
    :param path:
    :param api_key: the api_key associated with the request
    :return: None
    """
    resource_name: str = await get_resource_name(path=path)
    request_credit: int = resource_name_request_size.get(resource_name, 1)
    subscription_dict = await get_subscriptions_dict(api_key=api_key)

    subscription_dict["api_requests_balance"] -= request_credit
    await add_to_api_keys_to_subscriptions_cache(api_key=api_key, subscriptions_dict=subscription_dict)

    with next(sessions) as session:
        # TO Update subscription Model
        # TODO create a queue and put this in will make sense as demand for services increases
        await Subscriptions.update_subscription(subscription_data=subscription_dict, session=session)


async def process_credit_queue():
    """
        will run on the main app, as a separate thread to process
        request credit continuously
    :return:
    """
    while True:
        if take_credit_queue:
            async with lock:
                args = take_credit_queue.pop()
            if args:
                await take_credit_method(**args)
        await asyncio.sleep(5)


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
