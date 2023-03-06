import asyncio
import datetime

from fastapi import Request, FastAPI, HTTPException, Form
from starlette.responses import JSONResponse

from src import paypal_utils
from src.authentication import authenticate_admin, authenticate_app, authenticate_cloudflare_workers
from src.config import config_instance
from src.const import UUID_LEN
from src.database.account.account import Account
from src.database.apikeys.keys import ApiKeyModel
from src.database.database_sessions import sessions
from src.database.plans.plans import Subscriptions, Plans, Invoices
from src.email.email import email_process
from src.event_queues.invoice_queue import add_invoice_to_send, process_invoice_queues
from src.paypal_utils.paypal_plans import paypal_service
from src.utils.my_logger import init_logger
from src.utils.utils import create_id, calculate_invoice_date_range

management_logger = init_logger("management_aoi")
admin_app = FastAPI()


@admin_app.api_route(path="/_ipn/paypal/billing/subscription-created-activated",
                     methods=["GET", "POST"], include_in_schema=False)
async def paypal_subscription_activated_ipn(request: Request):
    """
        when subscription is created and activated call this endpoint
    :param request:
    :return:
    """
    return JSONResponse(content={'status': 'success'}, status_code=201)


@admin_app.api_route(path="/_ipn/paypal/<path:path>", methods=["GET", "POST"], include_in_schema=True)
@authenticate_admin
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
        management_logger.error('IPN verification failed: %s', response_text)
        return JSONResponse(content={'status': 'error'}, status_code=500)


@admin_app.api_route(path="/user", methods=["POST", "PUT"], include_in_schema=True)
@authenticate_app
async def create_update_user(request: Request, user_data: dict[str, str | int | bool]):
    """
        used to create new user record
    :param user_data:
    :param request:
    :return:
    """
    headers = {'Content-Type': 'application/json'}
    with next(sessions) as session:
        if request.method == "POST":
            management_logger.info("create user")
            email = user_data.get("email")
            user_instance = await Account.get_by_email(email=email, session=session)
            if not user_instance:
                user_instance = Account(**user_data)
                session.add(user_instance)
                account_dict = dict()
                # this will schedule an account confirmation email to be sent
                await email_process.send_account_confirmation_email(account_dict)
            else:
                raise HTTPException(detail="User already exist", status_code=401)

        elif request.method == "PUT":
            uuid = user_data.get('uuid')
            user_instance = await Account.get_by_uuid(uuid=uuid, session=session)
            user_instance = user_instance(**user_data)
            session.merge(user_instance)

        session.commit()

    return JSONResponse(content=user_instance.to_dict(), status_code=201, headers=headers)


@admin_app.api_route(path="/user/<path:path>", methods=["GET", "DELETE"], include_in_schema=True)
@authenticate_app
async def get_delete_user(request: Request, path: str):
    """
        used to update a user
    :param request:
    :param path:
    :return:
    """
    management_logger.info("Get Delete USER")

    headers = {'Content-Type': 'application/json'}
    uuid: str = path
    with next(sessions) as session:
        user_instance: Account = await Account.get_by_uuid(uuid=uuid, session=session)
        if request.method == "DELETE":
            user_instance.is_deleted = True
            session.merge(user_instance)
            session.commit()
            return JSONResponse(content={'message': 'successfully deleted user'},
                                status_code=201,
                                headers=headers)

        elif request.method == "GET":
            return JSONResponse(content=user_instance.to_dict(),
                                status_code=201,
                                headers=headers)

    return JSONResponse(content={'message': 'deleted user'}, status_code=201)


@admin_app.api_route(path="/subscriptions", methods=["POST", "PUT"], include_in_schema=True)
@authenticate_app
async def subscriptions(request: Request, subscription_data: dict[str, str | int | bool]):
    """
        create and update subscriptions
    :param request:
    :param subscription_data:
    :return:
    """
    management_logger.info("Subscriptions")
    headers = {'Content-Type': 'application:json'}

    with next(sessions) as session:

        if request.method == "POST":

            plan_id = subscription_data.get('plan_id')
            plan = await Plans.get_plan_by_plan_id(plan_id=plan_id, session=session)

            subscription_data.update({
                'subscription_id': create_id(UUID_LEN),
                'api_requests_balance': plan.plan_limit,
                'time_subscribed': datetime.datetime.now().timestamp()}
            )

            subscription_instance = await Subscriptions.subscribe(_data=subscription_data, session=session)
            from_date, to_date = calculate_invoice_date_range(today=datetime.datetime.now().timestamp())
            today = datetime.datetime.now().timestamp()

            invoice_data = {
                'subscription_id': subscription_data.get('subscription_id'),
                'invoice_id': create_id(UUID_LEN),
                'invoiced_amount': plan.charge_amount,
                'invoice_from_date': from_date,
                'invoice_to_date': to_date,
                'time_issued': today
            }

            invoice: Invoices = await Invoices.create_invoice(_data=invoice_data, session=session)

            session.add(subscription_instance)
            session.add(invoice)
            account = await Account.get_by_uuid(uuid=subscription_data.get("uuid"), session=session)
            await add_invoice_to_send(invoice=invoice.to_dict(), account=account.to_dict())

            session.commit()
            session.flush()
            # this last step creates a billing in paypal the client app must redirect the user to the url for verifying
            # the billing
            subscription_instance = await paypal_service.create_paypal_billing(plan=plan,
                                                                               subscription=subscription_instance)
            ADMIN = config_instance().EMAIL_SETTINGS.ADMIN
            sub_dict = dict(sender_email=ADMIN, recipient_email=account.email, client_name=account.name,
                            plan_name=plan.name)
            await email_process.send_subscription_welcome_email(**sub_dict)

        elif request.method == "PUT":
            """
                Upgrade or Downgrade Plan, thi only affect the net invoice
            """
            plan_id = subscription_data.get('plan_id')
            plan = await Plans.get_plan_by_plan_id(plan_id=plan_id, session=session)

            subscription_id = subscription_data.get('subscription_id')
            subscription_instance: Subscriptions = await Subscriptions.get_by_subscription_id(
                subscription_id=subscription_id, session=session)

            if subscription_instance.plan_id != plan_id:
                # create a method for upgrading or downgrading plan
                subscription_instance.api_requests_balance = plan.plan_limit
                subscription_instance.plan_id = plan_id
                subscription_instance.time_subscribed = datetime.datetime.now().timestamp()
                session.merge(subscription_instance)
                session.commit()

        return JSONResponse(content=subscription_instance.to_dict(), status_code=201, headers=headers)


@admin_app.api_route(path="/subscription/<path:path>", methods=["GET", "DELETE"], include_in_schema=True)
@authenticate_admin
async def get_delete_subscriptions(request: Request, path: str):
    """
        retrieve or delete subscriptions
        the delete action may usually mark records as deleted
    :param path:
    :param request:
    :return:
    """
    management_logger.info("Delete Subscriptions")
    return JSONResponse(content={'message': 'deleted subscription'}, status_code=201)


@admin_app.api_route(path="/paypal/subscriptions", methods=["GET"], include_in_schema=True)
@authenticate_admin
async def create_paypal_subscriptions(request: Request):
    """

    :param request:
    :return:
    """
    response = await paypal_service.create_paypal_billing_plans()
    print(response)
    return JSONResponse(content=response, status_code=201)


@admin_app.api_route(path="/plans", methods=["GET"], include_in_schema=True)
@authenticate_app
async def get_client_plans(request: Request):
    """

    :param request:
    :return:
    """
    with next(sessions) as session:
        plan_list = await Plans.get_all_plans(session=session)
    payload = [plan.to_dict() for plan in plan_list]

    return JSONResponse(content=payload, status_code=200)


@admin_app.on_event("startup")
async def admin_startup():
    """
    **admin_startup**
        :return:
    """
    # Needs more processes here
    asyncio.create_task(process_invoice_queues())


@admin_app.api_route(path="/cloudflare/init-gateway", methods=["GET", "POST"], include_in_schema=False)
@authenticate_cloudflare_workers
async def init_cloudflare_gateway(request: Request):
    """

    :param request:
    :return:
    """
    with next(sessions) as session:
        api_keys = await ApiKeyModel.get_all_active(session=session)
        payload = [api_key.to_dict() for api_key in api_keys]
    return JSONResponse(content=dict(status=True, api_keys=payload), status_code=200)
