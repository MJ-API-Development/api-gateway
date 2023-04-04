from fastapi import APIRouter, Request
import asyncio
import hmac
import random
import string
from starlette.responses import JSONResponse

from src.cache.cache import redis_cache
from src.database.account.account import Account, TwoFactorLoginData
from src.database.contact import Contacts
from src.database.database_sessions import sessions
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.management_api.email.email import email_process
from src.management_api.models.authentication import LoginData, AuthorizationRequest
from src.management_api.models.contact import ContactModel
from src.utils.my_logger import init_logger

contact_router = APIRouter()

contact_logger = init_logger('contact-logger')


@contact_router.api_route('/contacts', methods=['POST'])
def create_contact(request: Request, contact_data: ContactModel):
    """
        will create a new contact record on
    :param request:
    :param contact_data:
    :return:
    """
    with next(sessions) as session:
        contact_instance: Contacts = Contacts(**contact_data.dict())
        session.add(contact_instance)
        session.commit()

    _payload = dict(status=True, message="message sent successfully")
    # creating the header without payload to avoid a problem when a message is too big
    headers = await get_headers(user_data=_payload)
    _payload.update(payload=contact_instance)

    return JSONResponse(content=_payload, status_code=200, headers=headers)

