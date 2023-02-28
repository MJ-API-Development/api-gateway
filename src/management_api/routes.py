import asyncio
import datetime

from fastapi import Request, FastAPI, HTTPException
from starlette.responses import JSONResponse

from src.authentication import authenticate_admin, authenticate_client_app
from src.database.apikeys.keys import Account, UUID_LEN
from src.database.database_sessions import sessions
from src.database.plans.plans import Subscriptions, Plans, Invoices
from src.event_queues.invoice import process_invoice_queues, add_invoice_to_send
from src.utils.my_logger import init_logger
from src.utils.utils import create_id, calculate_invoice_date_range

management_logger = init_logger("management_aoi")
admin_app = FastAPI(
    title="EOD-STOCK-API - Admin Application",
    description="Adminstrative Tasks EndPoints",
    version="0.0.1",
    terms_of_service="https://www.eod-stock-api.site/terms",
    contact={
        "name": "EOD-STOCK-API - Admin",
        "url": "/contact",
        "email": "admin@eod-stock-api.site"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
    },
    docs_url="/_admin/docs",
    redoc_url="/_admin/redoc"
)


@authenticate_admin
async def paypal_payment_gateway_ipn(request: Request, path: str):
    """
        accept incoming payment notifications for
        the api and then process them
    :return:
    """
    management_logger.info("paypal IPN")


@authenticate_admin
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
            else:
                raise HTTPException(detail="User already exist", status_code=401)

        elif request.method == "PUT":
            uuid = user_data.get('uuid')
            user_instance = await Account.get_by_uuid(uuid=uuid, session=session)
            user_instance = user_instance(**user_data)
            session.merge(user_instance)

        session.commit()

    return JSONResponse(content=user_instance.to_dict(), status_code=201, headers=headers)


@authenticate_admin
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


@authenticate_client_app
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

        elif request.method == "PUT":
            """
                Upgrade or Dongrade Plan, thi only affect the net invoice
            """
            plan_id = subscription_data.get('plan_id')
            plan = await Plans.get_plan_by_plan_id(plan_id=plan_id, session=session)

            subscription_id = subscription_data.get('subscription_id')
            subscription_instance: Subscriptions = await Subscriptions.get_by_subscription_id(
                subscription_id=subscription_id,session=session)

            if subscription_instance.plan_id != plan_id:
                # create a method for upgrading or dongrading plan
                subscription_instance.api_requests_balance = plan.plan_limit
                subscription_instance.plan_id = plan_id
                subscription_instance.time_subscribed = datetime.datetime.now().timestamp()
                session.merge(subscription_instance)
                session.commit()


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


admin_app.add_route(path="/_ipn/payment-gateway/paypal/<path:path>", route=paypal_payment_gateway_ipn, methods=["GET"],
                    include_in_schema=True)
admin_app.add_route(path="/user/<path:path>", route=get_delete_user, methods=["GET", "DELETE"], include_in_schema=True)
admin_app.add_route(path="/user", route=create_update_user, methods=["POST", "PUT"], include_in_schema=True)
admin_app.add_route(path="/subscription/<path:path>", route=get_delete_subscriptions, methods=["GET", "DELETE"],
                    include_in_schema=True)
admin_app.add_route(path="/subscriptions", route=subscriptions, methods=["POST", "PUT"], include_in_schema=True),


@admin_app.on_event("startup")
async def admin_startup():
    """
    **admin_startup**
        :return:
    """
    asyncio.create_task(process_invoice_queues())
    # add more event queue tak here a they become available


# TODO add, method to change API Key