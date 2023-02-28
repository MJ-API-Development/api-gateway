from fastapi import Request, FastAPI, HTTPException
from starlette.responses import JSONResponse

from src.authentication import authenticate_admin
from src.authorize.authorize import NotAuthorized
from src.database.apikeys.keys import Account
from src.database.database_sessions import sessions
from src.utils.my_logger import init_logger

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
def paypal_payment_gateway_ipn(request: Request, path: str):
    """
        accept incoming payment notifications for
        the api and then process them
    :return:
    """
    management_logger.info("paypal IPN")


@authenticate_admin
def create_update_user(request: Request, user_data: dict[str, str | int | bool]):
    """
        used to create new user record
    :param user_data:
    :param request:
    :return:
    """
    headers = {'Content-Type': 'application/json'}
    with next(sessions) as session:
        if request.method == "post":
            management_logger.info("create user")
            email = user_data.get("email")
            user_instance = await Account.get_by_email(email=email, session=session)
            if not user_instance:
                user_instance = Account(**user_data)
                session.add(user_instance)
            else:
                raise HTTPException(detail="User already exist")

        elif request.method == "put":
            uuid = user_data.get('uuid')
            user_instance = await Account.get_by_uuid(uuid=uuid, session=session)
            user_instance = user_instance(**user_data)
            session.merge(user_instance)

        session.commit()

    return JSONResponse(content=user_instance.to_dict(), status_code=201, headers=headers)


@authenticate_admin
def get_delete_user(request: Request, path: str):
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

        elif request.method == "GET":
            return JSONResponse(content=user_instance.to_dict(),
                                status_code=201,
                                headers=headers)


@authenticate_admin
def subscriptions(request: Request, subscription_data: dict[str, str | int | bool]):
    """
        create and update subscriptions
    :param request:
    :param subscription_data:
    :return:
    """
    management_logger.info("Subscriptions")


@authenticate_admin
def get_delete_subscriptions(request: Request, path: str):
    """
        retrieve or delete subscriptions
        the delete action may ussually mark records as deleted
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
