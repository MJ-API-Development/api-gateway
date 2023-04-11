import time
from datetime import datetime
from sqlalchemy import Column, String, inspect, Float, ForeignKey

from src.const import UUID_LEN, NAME_LEN, EMAIL_LEN, STR_LEN
from src.database.database_sessions import Base, engine
from src.utils.utils import create_id


class Contacts(Base):
    """
        ORM Model for Contacts
    """
    __tablename__ = 'contact_messages'
    uuid: str = Column(String(UUID_LEN), index=True, nullable=True)
    contact_id: str = Column(String(UUID_LEN), primary_key=True, index=True)
    name: str = Column(String(NAME_LEN), index=True)
    email: str = Column(String(EMAIL_LEN), index=True)
    message: str = Column(String(STR_LEN))
    timestamp = Column(Float, index=True)

    def init(self, uuid: str, contact_id: str, name: str, email: str, message: str, timestamp: float):
        """

        :param uuid:
        :param contact_id:
        :param name:
        :param email:
        :param message:
        :param timestamp:
        :return:
        """

        self.uuid = uuid if uuid else create_id(UUID_LEN)
        self.contact_id = contact_id if contact_id else create_id(UUID_LEN)
        if (name is None) or (email is None) or (message is None):
            raise ValueError("Name, Email, and Message are required")
        self.name, self.email, self.message = name, email, message

        self.timestamp = timestamp if timestamp and isinstance(timestamp, float | int) else time.monotonic()

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    def to_dict(self) -> dict[str, str | int | float]:
        """will return a dict for contacts"""
        return {
            'uuid': self.uuid,
            'contact_id': self.contact_id,
            'name': self.name,
            'email': self.email,
            'message': self.message,
            'datetime': self.datetime,
            'timestamp': self.timestamp}