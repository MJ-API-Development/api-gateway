import asyncio
import time
from functools import wraps

from fastapi import HTTPException
from starlette import status

from src.apikeys.keys import api_keys, cache_api_keys, get_session, ApiKeyModel
from src.authorize.resources import get_resource_name, resource_name_request_size
from src.plans.plans import Subscriptions, Plans
from src.views_cache.cache import cached

api_keys_lookup = api_keys.get
cache_api_keys_func = cache_api_keys

take_credit_queue = []


class NotAuthorized(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.status_code = 403


def auth_and_rate_limit(func):
    # noinspection PyTypeChecker
    @wraps(func)
    async def wrapper(*args, **kwargs):
        api_key = kwargs.get('api_key')
        path = kwargs.get('path')
        if api_key is not None:
            if api_key not in api_keys:
                cache_api_keys_func()  # Update api_keys if the key is not found
                if api_key not in api_keys:
                    # user not authorized to access this routes
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid API Key')

            now = time.time()
            duration: int = api_keys_lookup(api_key, {}).get('duration')
            limit: int = api_keys_lookup(api_key, {}).get('rate_limit')

            if now - api_keys_lookup(api_key, {}).get('last_request_timestamp') > duration:
                api_keys[api_key]['requests_count'] = 0

            if api_keys_lookup(api_key, {}).get('requests_count') >= limit:
                # TODO consider returning a JSON String with data on the rate rate_limit and how long to wait
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                    detail='Rate rate_limit exceeded')

            # updating number of requests and timestamp
            api_keys[api_key]['requests_count'] += 1
            # noinspection PyTypeChecker
            api_keys[api_key]['last_request_timestamp'] = now

        # verifying if user can access this resource
        if await is_resource_authorized(path_param=path, api_key=api_key):
            if await monthly_credit_available(api_key=api_key):
                # will execute the api if monthly credit is available or monthly limit
                # is a soft limit, in which case the client will incur extra charges
                return await func(*args, **kwargs)
            mess: str = """
                Your Monthly plan request limit has been reached.
                 please upgrade your plan 
            """
            raise NotAuthorized(message=mess)

        raise NotAuthorized(message="Request not Authorized for this plan")

    return wrapper


@cached
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
    with get_session()() as session:
        client_api_model: ApiKeyModel = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
        subscription: Subscriptions = client_api_model.subscription
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
    with get_session()() as session:
        client_api_model: ApiKeyModel = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
        subscription_instance: Subscriptions = client_api_model.subscription
        plan_instance: Plans = await Plans.get_plan_by_plan_id(plan_id=subscription_instance.plan_id, session=session)
        if plan_instance.plan_limit <= subscription_instance.api_requests_balance:
            # if hard_limit is true then monthly credit is not available
            return not plan_instance.is_hard_limit()
        return True


async def create_take_credit_args(api_key: str, path: str):
    """
    **take_credit**
        will add the arguments to the processing queue for the take_credit method
    :param path:
    :param api_key:
    :return: None
    """
    resource_name: str = await get_resource_name(path=path)
    request_credit: int = resource_name_request_size.get(resource_name, 1)
    take_credit_queue.append(dict(api_key=api_key, request_credit=request_credit))


async def take_credit_method(api_key: str, request_credit: int):
    """

    :param request_credit: the size of api_balance in request which will be subtracted from the user subscription
    :param api_key: the api_key associated with the request
    :return: None
    """
    # TODO need to speed this up considerably
    with get_session()() as session:
        client_api_model: ApiKeyModel = await ApiKeyModel.get_by_apikey(api_key=api_key, session=session)
        subscription_instance: Subscriptions = client_api_model.subscription
        subscription_instance.api_requests_balance -= request_credit
        # The Purpose here is to update the subscription model so it reflects the most
        # recent api_requests_balance
        session.commit(subscription_instance)


async def process_credit_queue():
    """
        TODO - use a separate client to process credit_queue
        will run on the main app, as a separate thread to process
        request credit continuously
    :return:
    """
    while True:
        args = take_credit_queue.pop()
        if args:
            await take_credit_method(**args)
        await asyncio.sleep(5)
