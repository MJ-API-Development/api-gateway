from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from src.database.contact import Contacts
from src.database.database_sessions import sessions
from src.management_api.admin.authentication import get_headers, authenticate_app
from src.management_api.models.contact import ContactModel
from src.utils.my_logger import init_logger

contact_router = APIRouter()

contact_logger = init_logger('contact-logger')


@contact_router.api_route('/contacts', methods=['POST'])
@authenticate_app
async def create_contact(request: Request, contact_data: ContactModel):
    """
        will create a new contact record on
    :param request:
    :param contact_data:
    :return:
    """
    with next(sessions) as session:
        Contacts.create_if_not_exists()
        contact_instance: Contacts = Contacts(**contact_data.dict())
        session.add(contact_instance)
        session.commit()

        _payload = dict(status=True, message="message sent successfully")
        # creating the header without payload to avoid a problem when a message is too big
        headers = await get_headers(user_data=_payload)
        _payload.update(payload=contact_instance.to_dict())

    return JSONResponse(content=_payload, status_code=200, headers=headers)

