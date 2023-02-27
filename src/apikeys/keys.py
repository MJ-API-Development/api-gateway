from __future__ import annotations

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.database.database_sessions import sessions, Base, sessionType
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

    def to_dict(self) -> dict[str, str]:
        return {
            "uuid": self.uuid,
            "first_name": self.first_name,
            "second_name": self.second_name,
            "surname": self.surname,
            "email": self.email,
            "cell": self.cell,
            "is_admin": self.is_admin
        }


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
            "rate_limit": self.rate_limit,
            "is_active": self.is_active,
            "subscription": self.subscription,
            "account": self.account}

    @classmethod
    async def get_by_apikey(cls, api_key: str, session: sessionType) -> ApiKeyModel:
        """
        :param api_key:
        :param session:
        :return:
        """
        return session.query(cls).filter(cls.api_key == api_key).first()


def cache_api_keys():
    with next(sessions) as session:
        db_keys = session.query(ApiKeyModel).all()
        api_keys.update({db_key.api_key: {'requests_count': 0,
                                          'last_request_timestamp': 0,
                                          'duration': db_key.duration,
                                          'rate_limit': db_key.rate_limit} for db_key in db_keys})


def create_admin_key():
    with next(sessions) as session:
        api_key = ApiKeyModel(uuid=create_id(size=UUID_LEN),
                              api_key=create_id(size=UUID_LEN),
                              subscription_id=create_id(size=UUID_LEN),
                              duration=ONE_MINUTE,
                              limit=30, is_active=True)
        session.add(api_key)
        session.commit()
