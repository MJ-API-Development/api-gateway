from fastapi import APIRouter, Request
from fastapi.params import Form
from starlette.responses import JSONResponse

from src import paypal_utils
from src.config import config_instance
from src.database.database_sessions import sessions
from src.database.plans.plans import Subscriptions
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.management_api.models.paypal import PayPalIPN
from src.paypal_utils.paypal_plans import paypal_service
from src.utils.my_logger import init_logger

paypal_router = APIRouter()
paypal_logger = init_logger("paypal_router")


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
@authenticate_app
async def paypal_ipn(request: Request, ipn: PayPalIPN):
    """
        this IPN will handle the following events
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/activated
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/cancelled
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/created
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/expired-suspended
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/payment-failed
         https://gateway.eod-stock-api.site/_admin/_ipn/paypal/reactivated

    :param request:
    :param ipn:
    :return:
    """
    paypal_url = 'https://ipnpb.paypal.com/cgi-bin/webscr'
    paypal_token = 'your_paypal_token_here'

    verify_data = ipn.dict()

    # Add the token to the data
    verify_data['cmd'] = '_notify-validate'

    response_text = await paypal_utils.verify_ipn(ipn_data=verify_data)

    if response_text != 'VERIFIED':
        # Update your database with the relevant information
        # e.g., subscription start date, end date, and payment status
        # Send notifications to the client and relevant parties
        # e.g., email notifications, webhook notifications
        return {'status': 'ERROR', 'message': 'Invalid IPN message'}
    elif ipn.payment_status == 'Completed':
        # Return a response to PayPal indicating that the IPN was handled successfully
        with next(sessions) as session:
            # TODO have to fix this somehow
            subscription_id: str = ipn.custom
            subscription_instance = await Subscriptions.get_by_subscription_id(subscription_id=subscription_id, session=session)
            # TODO Complete the process of subscribing here

        return JSONResponse(content={'status': 'success'}, status_code=200)
    elif ipn.payment_status == 'Cancelled':
        """cancel subscription"""
        with next(sessions) as session:
            subscription_id: str = ipn.custom

    return JSONResponse(content={'status': 'OK'}, status_code=200)


@paypal_router.api_route(path="/_ipn/paypal/billing/subscription-created-activated",
                         methods=["GET", "POST"], include_in_schema=False)
async def paypal_subscription_activated_ipn(request: Request):
    """
        when subscription is created and activated call this endpoint
    :param request:
    :return:
    """
    return JSONResponse(content={'status': 'success'}, status_code=201)


@paypal_router.api_route(path="/paypal/settings/{uuid}", methods=["GET"])
def paypal_settings(request: Request, uuid: str):
    """

    :param request:
    :param uuid:
    :return:
    """
    paypal_settings_dict: dict[str, str] = config_instance().PAYPAL_SETTINGS.dict()

    return JSONResponse(content=paypal_settings_dict, status_code=200, headers={'Content-type': 'application/json'})

    # return JSONResponse(content=paypal_settings_dict, status_code=200)
