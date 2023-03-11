import asyncio
import datetime
import hashlib
import hmac

from fastapi import Request, FastAPI, HTTPException, Form, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import paypal_utils
from src.authentication import authenticate_app, authenticate_cloudflare_workers
from src.authorize.authorize import NotAuthorized
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
admin_app = FastAPI(
    title="EOD-STOCK-API - ADMINISTRATOR",
    description="Administration Application for EOD Stock API",
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


class LoginData(BaseModel):
    email: str
    password: str


class AuthorizationRequest(BaseModel):
    """
        uuid: the client uuid
        path: the path in the admin app the client wants access to
        method = method of request which will be used to access the path
    """
    uid: str
    path: str
    method: str


async def create_header(secret_key: str, user_data: dict) -> str:
    data_str = ','.join([str(user_data[k]) for k in sorted(user_data.keys())])
    signature = hmac.new(secret_key.encode('utf-8'), data_str.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{data_str}|{signature}"


async def get_headers(user_data: dict) -> dict[str, str]:
    secret_key = config_instance().SECRET_KEY
    signature = await create_header(secret_key, user_data)
    return {'X-SIGNATURE': signature, 'Content-Type': 'application/json'}


def verify_signature(request):
    secret_key = config_instance().SECRET_KEY
    data_str, signature_header = request.headers.get('X-SIGNATURE', '')
    _signature = hmac.new(secret_key.encode('utf-8'), data_str.encode('utf-8'), hashlib.sha256).hexdigest()
    result = hmac.compare_digest(signature_header, _signature)
    print(f"Request Validation Result : {result}")
    return result


async def check_authorization(uuid: str | None, path: str, method: str) -> bool:
    """
    Function to check if user is authorized to access a specific route.
    Assume there is a map containing routes which normal users can access
    and routes that only admin users can access.
    :param uuid: The user's UUID.
    :param path: The path being accessed.
    :param method: The HTTP method being used.
    :return: True if the user is authorized, False otherwise.
    """
    # Map containing routes accessible by normal users and admin users
    user_routes = {
        "/home": ["GET"],
        "/dashboard": ["GET", "PUT"],
        "/profile": ["GET", "PUT"]
    }
    admin_routes = {
        "/admin/users": ["GET", "POST", "PUT", "DELETE"],
        "/admin/subscriptions": ["GET", "POST", "PUT", "DELETE"],
        "/admin/plans": ["GET", "POST", "PUT", "DELETE"]
    }

    if uuid is None or path is None or method is None:
        return False

    # Retrieve the user data based on the UUID
    with next(sessions) as session:
        user = await Account.get_by_uuid(uuid=uuid, session=session)

    # Check if the user is authorized to access the path
    if user is None:
        return False

    if path in user_routes and method in user_routes[path]:
        return True

    if user.is_admin and path in admin_routes and method in admin_routes[path]:
        # Check if the path is accessible only to admin users
        return True


@admin_app.api_route(path="/_ipn/paypal/billing/subscription-created-activated",
                     methods=["GET", "POST"], include_in_schema=False)
async def paypal_subscription_activated_ipn(request: Request):
    """
        when subscription is created and activated call this endpoint
    :param request:
    :return:
    """
    return JSONResponse(content={'status': 'success'}, status_code=201)


@admin_app.api_route(path="/_ipn/paypal/{path}", methods=["GET", "POST"], include_in_schema=True)
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
                # TODO look at this - Make this an ephemeral link, it other words it should expire after sometime
                verification_link = f"https://gateway.eod-stock-api.site/_admin/account/confirm/{account_dict.get('uuid')}"

                sender_email = config_instance().EMAIL_SETTINGS.ADMIN
                recipient_email = account_dict.get('email')
                client_name = account_dict.get('name')
                message_dict = dict(verification_link=verification_link, sender_email=sender_email,
                                    recipient_email=recipient_email, client_name=client_name)

                await email_process.send_account_confirmation_email(**message_dict)
            else:
                raise HTTPException(detail="User already exist", status_code=401)

        elif request.method == "PUT":
            uuid = user_data.get('uuid')
            user_instance = await Account.get_by_uuid(uuid=uuid, session=session)
            user_instance = user_instance(**user_data)
            session.merge(user_instance)

        session.commit()
        headers = await get_headers(user_data=user_instance.to_dict())
        return JSONResponse(content=user_instance.to_dict(), status_code=201, headers=headers)


@admin_app.api_route(path="/user/{path}", methods=["GET", "DELETE"], include_in_schema=True)
@authenticate_app
async def get_delete_user(request: Request, path: str):
    """
        used to update a user
    :param request:
    :param path:
    :return:
    """
    management_logger.info("Get Delete USER")

    uuid: str = path
    with next(sessions) as session:
        user_instance: Account = await Account.get_by_uuid(uuid=uuid, session=session)
        if request.method == "DELETE":
            user_instance.is_deleted = True
            session.merge(user_instance)
            session.commit()
            # TODO send a Goodbye Email
            message = {'message': 'successfully deleted user'}
            headers = await get_headers(user_data=message)
            return JSONResponse(content=message,
                                status_code=201,
                                headers=headers)

        elif request.method == "GET":
            # TODO Send a Login Email
            headers = await get_headers(user_data=user_instance.to_dict())
            return JSONResponse(content=user_instance.to_dict(),
                                status_code=201,
                                headers=headers)

    message = {'message': 'successfully deleted user'}
    headers = await get_headers(user_data=message)
    return JSONResponse(content={'message': 'deleted user'}, status_code=201, headers=headers)


@admin_app.api_route(path="/auth/login", methods=["POST"], include_in_schema=True)
@authenticate_app
async def login(login_data: LoginData):
    """
        used to update a user

    :param login_data:
    :return:
    """
    user_data: dict[str, str] = login_data.dict()
    email = user_data.get("email")
    password = user_data.get("password")
    with next(sessions) as session:
        user_instance = await Account.login(username=email, password=password, session=session)
        if user_instance:
            payload = dict(status=True, payload=user_instance.to_dict(), message="successfully logged in")
        else:
            payload = dict(status=False, payload={}, message="user not found")
    headers = await get_headers(user_data=user_instance.to_dict())
    return JSONResponse(content=payload, status_code=200, headers=headers)


@admin_app.api_route(path="/auth/authorize", methods=["POST"], include_in_schema=True)
@authenticate_app
async def authorization(auth_data: AuthorizationRequest):
    """
    **authorization**
        authorizes requests to specific resources within the admin application

    :param auth_data: authorization data
    :return: payload : dict[str, str| bool dict[str|bool]], status_code
    """
    user_data = auth_data.dict()
    uuid = user_data.get("uuid")
    path = user_data.get("path")
    method = user_data.get("method")

    is_authorized = await check_authorization(uuid=uuid, path=path, method=method)
    message = "user is authorized" if is_authorized else "user not authorized"
    payload = dict(status=True, payload=dict(is_authorized=is_authorized), message=message)
    headers = await get_headers(user_data=payload)
    return JSONResponse(content=payload, status_code=200, headers=headers)


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
    # TODO Refactor this method to include request authorization headers
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


@admin_app.api_route(path="/subscription/{path}", methods=["GET", "DELETE"], include_in_schema=True)
@authenticate_app
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
@authenticate_app
async def create_paypal_subscriptions(request: Request):
    """

    :param request:
    :return:
    """
    response = await paypal_service.create_paypal_billing_plans()
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
        **init_cloudflare_gateway**
                initialize cloudflare
    :param request:
    :return:
    """
    with next(sessions) as session:
        api_keys = await ApiKeyModel.get_all_active(session=session)
        payload = [api_key.to_dict() for api_key in api_keys]
    return JSONResponse(content=dict(status=True, api_keys=payload), status_code=200)


@admin_app.exception_handler(NotAuthorized)
async def admin_not_authorized(request: Request, exc: NotAuthorized):
    user_data = {"message": exc.message}

    return JSONResponse(
        status_code=exc.status_code,
        content=user_data, headers=await get_headers(user_data))
