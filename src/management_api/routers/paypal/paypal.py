from fastapi import APIRouter, Request
from fastapi.params import Form
from starlette.responses import JSONResponse

from src import paypal_utils
from src.database.database_sessions import sessions
from src.database.plans.plans import Subscriptions
from src.management_api.admin.authentication import authenticate_app
from src.paypal_utils.paypal_plans import paypal_service
from src.utils.my_logger import init_logger

paypal_router = APIRouter()
paypal_logger = init_logger("paypal_router")


@paypal_router.api_route(path="/paypal/subscriptions", methods=["GET"], include_in_schema=True)
@authenticate_app
async def create_paypal_subscriptions(request: Request):
    """
        TODO - create a PayPal Subscriptions Model
    :param request:
    :return:
    """
    response = await paypal_service.create_paypal_billing_plans()
    return JSONResponse(content=response, status_code=201)


@paypal_router.api_route(path="/_ipn/paypal/{path}", methods=["GET", "POST"], include_in_schema=True)
@authenticate_app
async def paypal_ipn(request: Request, custom_data: str = Form(...), txn_type: str = Form(...)):
    paypal_url = 'https://ipnpb.paypal.com/cgi-bin/webscr'
    paypal_token = 'your_paypal_token_here'

    # Get the IPN data from PayPal
    ipn_data = await request.form()

    # Convert the form data to a dictionary
    ipn_dict = {key: value for key, value in ipn_data.items()}

    # Add the token to the data
    ipn_dict['cmd'] = '_notify-validate'
    ipn_dict['custom'] = custom_data
    ipn_dict['txn_type'] = txn_type
    response_text = await paypal_utils.verify_ipn(ipn_data=ipn_dict)

    if response_text == 'VERIFIED':
        # Update your database with the relevant information
        # e.g., subscription start date, end date, and payment status
        # Send notifications to the client and relevant parties
        # e.g., email notifications, webhook notifications
        with next(sessions) as session:
            # TODO have to fix this somehow
            subscription_id: str = custom_data.get('subscription_id')
            subscription_instance = await Subscriptions.get_by_subscription_id(subscription_id=subscription_id,
                                                                               session=session)

        # Return a response to PayPal indicating that the IPN was handled successfully
        return JSONResponse(content={'status': 'success'}, status_code=200)

    else:
        # If the IPN is not verified, log the error and return a 500 status code
        paypal_logger.error('IPN verification failed: %s', response_text)
        return JSONResponse(content={'status': 'error'}, status_code=500)


@paypal_router.api_route(path="/_ipn/paypal/billing/subscription-created-activated",
                         methods=["GET", "POST"], include_in_schema=False)
async def paypal_subscription_activated_ipn(request: Request):
    """
        when subscription is created and activated call this endpoint
    :param request:
    :return:
    """
    return JSONResponse(content={'status': 'success'}, status_code=201)
