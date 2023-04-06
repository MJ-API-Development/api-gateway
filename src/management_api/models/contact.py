from pydantic import BaseModel


class ContactModel(BaseModel):
    uuid: str
    contact_id: str
    name: str
    email: str
    message: str
    timestamp: float

    class Config:
        title = "Contact Model"
        extra = "forbid"
