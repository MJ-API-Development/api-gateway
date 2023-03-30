from datetime import datetime

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from src.config import config_instance
from src.const import UUID_LEN
from src.database.account.account import Account
from src.database.database_sessions import sessions
from src.database.plans.plans import Plans, Subscriptions, Invoices
from src.management_api.email.email import email_process
from src.event_queues.invoice_queue import add_invoice_to_send
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.management_api.models.subscriptions import SubscriptionCreate, SubscriptionUpdate
from src.paypal_utils.paypal_plans import paypal_service
from src.utils.my_logger import init_logger
from src.utils.utils import create_id, calculate_invoice_date_range

subscriptions_router = APIRouter()
sub_logger = init_logger("subscriptions_router")


@subscriptions_router.api_route(path="/subscriptions", methods=["POST", "PUT"], include_in_schema=True)
@authenticate_app
async def create_subscription(subscription_data: SubscriptionCreate, request: Request):
    """
        create and update subscriptions
    :param subscription_data:
    :return:
    """
    sub_logger.info("Subscriptions")
    headers = {'Content-Type': 'application:json'}
    # TODO Refactor this method to include request authorization headers
    with next(sessions) as session:
        plan_id = subscription_data.plan_id
        plan = await Plans.get_plan_by_plan_id(plan_id=plan_id, session=session)
        subscribe_dict = subscription_data.dict()
        subscribe_dict.update({
            'subscription_id': create_id(UUID_LEN),
            'api_requests_balance': plan.plan_limit,
            'time_subscribed': datetime.now().timestamp()}
        )

        subscription_instance = await Subscriptions.subscribe(_data=subscribe_dict, session=session)
        from_date, to_date = calculate_invoice_date_range(today=datetime.now().timestamp())
        today = datetime.now().timestamp()

        invoice_data = {
            'subscription_id': subscription_instance.subscription_id,
            'invoice_id': create_id(UUID_LEN),
            'invoiced_amount': plan.charge_amount,
            'invoice_from_date': from_date,
            'invoice_to_date': to_date,
            'time_issued': today
        }

        invoice: Invoices = await Invoices.create_invoice(_data=invoice_data, session=session)

        session.add(subscription_instance)
        session.commit()
        session.add(invoice)
        account = await Account.get_by_uuid(uuid=subscription_data.uuid, session=session)
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
        payload = dict(status=True,
                       payload=subscription_instance.to_dict(),
                       message="successfully created a new subscription")
        _headers = await get_headers(user_data=payload)
        return JSONResponse(content=payload, status_code=201, headers=_headers)


@subscriptions_router.api_route(path="/subscriptions", methods=["PUT"], include_in_schema=True)
@authenticate_app
async def update_subscription(subscription_data: SubscriptionUpdate, request: Request):
    """
            Upgrade or Downgrade Plan, thi only affect the net invoice
        """
    with next(sessions) as session:
        plan_id = subscription_data.plan_id
        plan = await Plans.get_plan_by_plan_id(plan_id=plan_id, session=session)

        subscription_id = subscription_data.subscription_id
        subscription_instance: Subscriptions = await Subscriptions.get_by_subscription_id(
            subscription_id=subscription_id, session=session)

        if subscription_instance.plan_id != plan_id:
            # create a method for upgrading or downgrading plan
            subscription_instance.api_requests_balance = plan.plan_limit
            subscription_instance.plan_id = plan_id
            subscription_instance.time_subscribed = datetime.now().timestamp()
            session.merge(subscription_instance)
            session.commit()
        else:
            # TODO update only changed fields
            subscription_data_dict = subscription_data.dict(exclude_unset=True)
            for field, value in subscription_data_dict.items():
                setattr(subscription_instance, field, value)
            session.merge(subscription_instance)
            session.commit()

    payload = dict(status=True, payload=subscription_instance.to_dict(), message="subscription updated")
    _headers = await get_headers(user_data=payload)
    return JSONResponse(content=payload, status_code=201, headers=_headers)


@subscriptions_router.api_route(path="/subscription/{subscription_id}", methods=["DELETE"], include_in_schema=True)
@authenticate_app
async def de_activate_subscriptions(subscription_id: str, request: Request):
    """
        de activate subscriptions
        the delete action may usually mark records as deleted
    :param request:
    :param subscription_id:

    :return:
    """
    with next(sessions) as session:
        subscription_instance: Subscriptions = await Subscriptions.get_by_subscription_id(
            subscription_id=subscription_id,
            session=session)

        if subscription_instance:
            subscription_instance.set_is_active(is_active=False)
            session.merge(subscription_instance)
            session.commit()
            payload = dict(status=True, payload=subscription_instance.to_dict(),
                           message='successfully deactivated subscription')

            _headers = await get_headers(user_data=payload)

        else:
            payload = dict(status=True, payload={},
                           message='Successfully retrieved subscription')
            _headers = await get_headers(user_data=payload)

    return JSONResponse(content=payload, status_code=200, headers=_headers)


@subscriptions_router.api_route(path="/subscription/{subscription_id}", methods=["DELETE"], include_in_schema=True)
@authenticate_app
async def re_activate_subscriptions(subscription_id: str, request: Request):
    """
    **re_activate_subscription**
        re-activate previously de-activated subscription

    :param request:
    :param subscription_id: id of the subscription to activate

    :return:
    """
    with next(sessions) as session:
        subscription_instance: Subscriptions = await Subscriptions.get_by_subscription_id(
            subscription_id=subscription_id,
            session=session)

        if subscription_instance:
            subscription_instance.set_is_active(is_active=True)
            session.merge(subscription_instance)
            session.commit()
            payload = dict(status=True, payload=subscription_instance.to_dict(),
                           message='successfully activated subscription')

            _headers = await get_headers(user_data=payload)

        else:
            payload = dict(status=True, payload={},
                           message='Successfully retrieved subscription')
            _headers = await get_headers(user_data=payload)

    return JSONResponse(content=payload, status_code=200, headers=_headers)


@subscriptions_router.api_route(path="/subscription/{subscription_id}", methods=["DELETE"], include_in_schema=True)
@authenticate_app
async def get_subscription(subscription_id: str, request: Request):
    """
    **get_subscription**

        retrieve or delete subscriptions
        the delete action may usually mark records as deleted

    :param request:
    :param subscription_id: id of the subscription to fetch

    :return:
    """
    with next(sessions) as session:
        subscription_instance = await Subscriptions.get_by_subscription_id(subscription_id=subscription_id,
                                                                           session=session)
        if subscription_instance:
            payload = dict(status=True, payload=subscription_instance.to_dict(),
                           message='Successfully retrieved subscription')
            _headers = await get_headers(user_data=payload)
        else:
            payload = dict(status=True, payload={},
                           message='Successfully retrieved subscription')
            _headers = await get_headers(user_data=payload)

    return JSONResponse(content=payload, status_code=200, headers=_headers)


@subscriptions_router.api_route(path="/plans/{plan_id}", methods=["GET"], include_in_schema=True)
@authenticate_app
async def get_plan(plan_id: str, request: Request):
    """

    :param plan_id:
    :param request:
    :return:
    """
    with next(sessions) as session:
        plan_instance = await Plans.get_plan_by_plan_id(plan_id=plan_id, session=session)
        if plan_instance:
            payload = dict(status=True, payload=plan_instance.to_dict(), message='Successfully retrieved plan')
            _headers = await get_headers(user_data=payload)
        else:
            payload = dict(status=True, payload={},
                           message='Successfully retrieved subscription')
            _headers = await get_headers(user_data=payload)

        return JSONResponse(content=payload, status_code=200, headers=_headers)


@subscriptions_router.api_route(path="/plans", methods=["GET"], include_in_schema=True)
@authenticate_app
async def get_all_plans(request: Request):
    """
        returns all plans
    :param plan_id:
    :param request:
    :return:
    """
    with next(sessions) as session:
        plan_instance_list = await Plans.get_all_plans(session=session)
        _payload = [plan.to_dict() for plan in plan_instance_list] if plan_instance_list else []
        sub_logger.info(f"GET ALL PLANS : {_payload}")

        payload = dict(status=True,  message='Successfully retrieved plan')
        _headers = await get_headers(user_data=payload)
        payload.update(payload=_payload)

    return JSONResponse(content=payload, status_code=200, headers=_headers)
