from fastapi import Request, FastAPI
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


def paypal_payment_gateway_ipn(request: Request, path: str):
    """
        accept incoming payment notifications for
        the api and then process them
    :return:
    """
    management_logger.info("paypal IPN")


def create_user(request: Request, user_data: dict[str, str | int | bool]):
    """

    :param user_data:
    :param request:
    :return:
    """
    management_logger.info("create user")


def get_update_user(request: Request, path: str):
    """

    :param request:
    :param path:
    :return:
    """
    management_logger.info("Updated USER")


def subscriptions(request: Request):
    """
        create and update subscriptions
    :param request:
    :return:
    """
    management_logger.info("Subscriptions")


def get_delete_subscriptions(request: Request, path: str):
    """

    :param path:
    :param request:
    :return:
    """
    management_logger.info("Delete Subscriptions")


admin_app.add_route(path="/_ipn/payment-gateway/paypal/<path:path>", route=paypal_payment_gateway_ipn, methods=["GET"], include_in_schema=True)
admin_app.add_route(path="/user/<path:path>", route=get_update_user, methods=["GET", "DELETE"], include_in_schema=True)
admin_app.add_route(path="/user", route=create_user, methods=["POST", "PUT"], include_in_schema=True)
admin_app.add_route(path="/subscription/<path:path>", route=get_delete_subscriptions, methods=["GET", "DELETE"], include_in_schema=True)
admin_app.add_route(path="/subscriptions", route=subscriptions, methods=["POST", "PUT"], include_in_schema=True),
