import string
from typing import Self

from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from src.config import config_instance
from src.plans.plans import Subscriptions
from src.utils.utils import create_id

# Define a dict to store API Keys and their rate rate_limit data
# Cache tp store API KEys
api_keys: dict[str, dict[str, int]] = {}

ONE_MINUTE = 60 * 60
UUID_LEN: int = 16
STR_LEN: int = 255
NAME_LEN: int = 128
EMAIL_LEN: int = 255
CELL_LEN: int = 13
API_KEY_LEN: int = 64

DATABASE_URL = config_instance().DATABASE_SETTINGS.SQL_DB_URL
engine = create_engine(DATABASE_URL)

# Define a SQLAlchemy model for API Keys
Base = declarative_base()
sessionType = Session


def get_session():
    return sessionmaker(bind=engine)


class Account(Base):
    """
        User Account ORM
    """
    __tablename__ = "accounts"
    uuid: str = Column(String(UUID_LEN), primary_key=True, index=True)
    api_key: str = Column(String(UUID_LEN), ForeignKey("eod_api_keys.api_key"))
    first_name: str = Column(String(NAME_LEN), index=True)
    second_name: str = Column(String(NAME_LEN), index=True)
    surname: str = Column(String(NAME_LEN), index=True)
    email: str = Column(String(EMAIL_LEN), index=True, unique=True)
    cell: str = Column(String(CELL_LEN), index=True, unique=True)
    password_hash: str = Column(String(STR_LEN), index=True)
    is_admin: bool = Column(Boolean, default=False)


# Define a Pydantic model for API Key validation
class ApiKey(BaseModel):
    uuid: str
    api_key: str
    subscription_id: str
    duration: int
    rate_limit: int


class ApiKeyModel(Base):
    """
        api key model
    """
    __tablename__ = 'eod_api_keys'
    uuid: str = Column(String(UUID_LEN), ForeignKey("accounts.uuid"), index=True)
    api_key: str = Column(String(API_KEY_LEN), primary_key=True, index=True)
    duration: int = Column(Integer)
    rate_limit: int = Column(Integer)
    is_active: bool = Column(Boolean, default=True)
    subscription = relationship("Subscriptions", uselist=False, foreign_keys=[Subscriptions.uuid])
    account = relationship("Account", uselist=False, foreign_keys=[Account.uuid])

    def to_dict(self) -> dict[str, str]:
        return {
            "uuid": self.uuid,
            "api_key": self.api_key,
            "subscription_id": self.subscription_id,
            "duration": self.duration,
            "rate_limit": self.rate_limit}

    @classmethod
    async def get_by_apikey(cls, api_key: str, session: sessionType) -> Self:
        """

        :param api_key:
        :param session:
        :return:
        """
        return session.query(cls).filter(cls.api_key == api_key).first()


def cache_api_keys():
    with get_session()() as session:
        db_keys = session.query(ApiKeyModel).all()
        api_keys.update({db_key.api_key: {'requests_count': 0,
                                          'last_request_timestamp': 0,
                                          'duration': db_key.duration,
                                          'rate_limit': db_key.rate_limit} for db_key in db_keys})


def create_admin_key():
    with get_session()() as session:
        api_key = ApiKeyModel(uuid=create_id(size=UUID_LEN),
                              api_key=create_id(size=UUID_LEN),
                              subscription_id=create_id(size=UUID_LEN),
                              duration=ONE_MINUTE,
                              limit=30, is_active=True)
        session.add(api_key)
        session.commit()
