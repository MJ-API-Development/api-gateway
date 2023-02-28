
from datetime import datetime
from sqlalchemy import Column, String, inspect, Integer, Float, ForeignKey

from src.databases.const import UUID_LEN, NAME_LEN, EMAIL_LEN, STR_LEN
from src.databases.models.sql import Base, mysql_instance
from src.utils import date_from_timestamp


class Contacts(Base):
    """
        ORM Model for Contacts
    """
    __tablename__ = 'contact_messages'
    uuid = Column(String(UUID_LEN), index=True, nullable=True)
    contact_id = Column(String(UUID_LEN), primary_key=True, index=True)
    name = Column(String(NAME_LEN), index=True)
    email = Column(String(EMAIL_LEN), ForeignKey("accounts.email"), index=True)
    message = Column(String(STR_LEN))
    timestamp = Column(Float, index=True)

    @property
    def datetime(self) -> datetime:
        return date_from_timestamp(self.timestamp)

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(mysql_instance.engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=mysql_instance.engine)

