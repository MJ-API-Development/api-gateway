from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

from src.authentication import authenticate_app, authenticate_cloudflare_workers
from src.authorize.authorize import NotAuthorized
from src.database.apikeys.keys import ApiKeyModel
from src.database.database_sessions import sessions
from src.database.plans.plans import Plans
from src.management_api.admin.authentication import get_headers
from src.management_api.routers.authorization.authorization import auth_router
from src.management_api.routers.contact.contact_route import contact_router
from src.management_api.routers.logs.logs import log_router
from src.management_api.routers.paypal.paypal import paypal_router
from src.management_api.routers.subscriptions.subscriptions import subscriptions_router
from src.management_api.routers.users.users import users_router
from src.utils.my_logger import init_logger

management_logger = init_logger("management_api")
admin_app = FastAPI(
    title="EOD-STOCK-API - CLIENT ADMINISTRATOR API",
    description="Client Administration API for EOD Stock API",
    version="0.0.12",
    terms_of_service="https://www.eod-stock-api.site/terms",
    contact={
        "name": "MJ API Development",
        "url": "https://www.eod-stock-api.site/contact",
        "email": "info@eod-stock-api.site"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/open-api"
)


@admin_app.middleware(middleware_type="http")
async def check_if_valid_request(request: Request, call_next):
    """
    **check_if_valid_request**
        Admin API Validations
    :param request:
    :param call_next:
    :return:
    """
    path = request.url
    management_logger.info(f"on entry into Management API : {path} method: {request.method}")
    response = await call_next(request)
    management_logger.info(f"on exit from Management API : {response.status_code} {response.text}")
    return response


admin_app.include_router(users_router)
admin_app.include_router(auth_router)
admin_app.include_router(log_router)
admin_app.include_router(paypal_router)
admin_app.include_router(subscriptions_router)
admin_app.include_router(contact_router)


@admin_app.api_route(path="/plans", methods=["GET"], include_in_schema=True)
@authenticate_app
async def get_client_plans():
    """
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
    ADMIN API startup procedures
        :return:
    """
    # Needs more processes here
    print("admin app started")
    # asyncio.create_task(process_invoice_queues())


@admin_app.api_route(path="/cloudflare/init-gateway", methods=["GET", "POST"], include_in_schema=False)
@authenticate_cloudflare_workers
async def init_cloudflare_gateway():
    """
    **init_cloudflare_gateway**
        at the gateway -
        **init_cloudflare_gateway**
                initialize cloudflare
    :return:
    """
    with next(sessions) as session:
        api_keys = await ApiKeyModel.get_all_active(session=session)
        payload = [api_key.to_dict()['api_key'] for api_key in api_keys]

    return JSONResponse(content=dict(status=True, api_keys=payload), status_code=200)


# noinspection PyUnusedLocal
@admin_app.exception_handler(NotAuthorized)
async def admin_not_authorized(request: Request, exc: NotAuthorized):
    """
    **admin_not_authorized**
        This exception will be thrown whenever Authorization has not passed.
    :param request:
    :param exc:
    :return:
    """
    user_data = {"message": exc.message}
    management_logger.info(f"Error occurred: {str(exc)}")
    return JSONResponse(
        status_code=exc.status_code,
        content=user_data, headers=await get_headers(user_data))


# noinspection PyUnusedLocal
@admin_app.exception_handler(Exception)
async def handle_all_exceptions(request: Request, exc: Exception):
    management_logger.info(f"Error processing request : {str(exc)}")
    error_data = {'message': 'error processing request'}
    return JSONResponse(content=error_data,
                        status_code=500,
                        headers=await get_headers(error_data))


# noinspection PyUnusedLocal
@admin_app.get("/_ah/warmup", include_in_schema=False)
async def status_check(request: Request):
    return JSONResponse(content={'status': 'OK'}, status_code=200, headers={"Content-Type": "application/json"})
