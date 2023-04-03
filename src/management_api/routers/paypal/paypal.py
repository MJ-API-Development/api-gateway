import functools

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from src import paypal_utils
from src.authorize.authorize import NotAuthorized
from src.config import config_instance
from src.database.database_sessions import sessions
from src.database.plans.plans import Subscriptions
from src.management_api.admin.authentication import authenticate_app
from src.management_api.models.paypal import PayPalIPN
from src.paypal_utils.paypal_plans import paypal_service
from src.utils.my_logger import init_logger

paypal_router = APIRouter()
paypal_logger = init_logger("paypal_router")


async def verify_paypal_ipn(ipn: PayPalIPN):
    """will check if paypal ipn is verified if not throws an error"""
    verify_data = ipn.dict()
    response_text = await paypal_utils.verify_ipn(ipn_data=verify_data)
    # NOTE Verify if the request comes from PayPal if not Raise Error and exit
    if response_text.casefold() != 'VERIFIED'.casefold():
        raise NotAuthorized(message="Invalid IPN Request")
    return True


@paypal_router.api_route(path="/paypal/subscriptions", methods=["GET"], include_in_schema=True)
# @authenticate_app
async def create_paypal_subscriptions(request: Request):
    """
        TODO - create a PayPal Subscriptions Model
    :param request:
    :return:
    """
    response = await paypal_service.create_paypal_billing_plans()
    paypal_logger.info(f"Paypal Subscriptions : {response}")
    return JSONResponse(content=response, status_code=201)


@paypal_router.api_route(path="/_ipn/paypal/{path}", methods=["GET", "POST"], include_in_schema=True)
async def paypal_ipn(request: Request, path: str, ipn: PayPalIPN):
    """
    **paypal_ipn**

        this IPN will handle the following events from paypal and then take the
        required actions on the user account related to the PayPal Action / Event
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/activated
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/cancelled
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/created
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/expired-suspended
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/payment-failed
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/reactivated

    :param path:
    :param request:
    :param ipn:
    :return:
    """
    # NOTE Authenticates the IPN Message
    await verify_paypal_ipn(ipn=ipn)

    # Changes Subscription State depending on IPN Message
    async def change_subscription_state(_subscription_id: str, state: bool):
        """change subscription state depending on the request state"""
        with next(sessions) as _session:
            # TODO verify that the subscription ID here is the same as the one we had when subscribing
            _subscription_instance: Subscriptions = await Subscriptions.get_by_subscription_id(
                subscription_id=_subscription_id, session=_session)
            _subscription_instance._is_active = state
            _session.merge(_subscription_instance)
            _session.commit()
        return JSONResponse(content={'status': 'OK'}, status_code=200)

    # NOTE: select appropriate state depending on the ipn
    _ipn_state_selector = {'cancelled': functools.partial(change_subscription_state, state=False),
                           'activated': functools.partial(change_subscription_state, state=True),
                           'expired': functools.partial(change_subscription_state, state=False),
                           'suspended': functools.partial(change_subscription_state, state=False),
                           'payment-failed': functools.partial(change_subscription_state, state=False),
                           'reactivated': functools.partial(change_subscription_state, state=False)}
    # TODO consider sending notification Emails triggered by events here
    return await _ipn_state_selector.get(path.casefold())(_subscription_id=ipn.custom)


@paypal_router.api_route(path="/paypal/settings/{uuid}", methods=["GET"])
@authenticate_app
def paypal_settings(request: Request, uuid: str):
    """
    **paypal_settings**
        This will return the settings for PayPal
    :param request:
    :param uuid:
    :return:
    """
    paypal_settings_dict: dict[str, str] = config_instance().PAYPAL_SETTINGS.dict()
    return JSONResponse(content=paypal_settings_dict, status_code=200, headers={'Content-type': 'application/json'})

    # return JSONResponse(content=paypal_settings_dict, status_code=200)
