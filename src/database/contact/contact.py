
from datetime import datetime
from sqlalchemy import Column, String, inspect, Integer, Float, ForeignKey

from src.const import UUID_LEN, NAME_LEN, EMAIL_LEN, STR_LEN
from src.database.database_sessions import Base, engine


class Contacts(Base):
    """
        ORM Model for Contacts
    """
    __tablename__ = 'contact_messages'
    uuid: str = Column(String(UUID_LEN), index=True, nullable=True)
    contact_id: str = Column(String(UUID_LEN), primary_key=True, index=True)
    name: str = Column(String(NAME_LEN), index=True)
    email: str = Column(String(EMAIL_LEN), ForeignKey("accounts.email"), index=True)
    message: str = Column(String(STR_LEN))
    timestamp = Column(Float, index=True)

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

