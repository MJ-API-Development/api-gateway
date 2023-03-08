from __future__ import annotations

import asyncio
import datetime

import pymysql
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, inspect
from sqlalchemy.orm import relationship
from typing_extensions import Self

from src.database.database_sessions import sessions, Base, sessionType, engine
from src.database.plans.plans import Subscriptions, Plans
from src.utils.utils import create_id
apikeys_lock = asyncio.Lock()
# Define a dict to store API Keys and their rate rate_limit data
# Cache tp store API KEys
# TODO use Async QUEUE
api_keys: dict[str, dict[str, int]] = {}

ONE_MINUTE = 60 * 60
UUID_LEN: int = 16
STR_LEN: int = 255
NAME_LEN: int = 128
EMAIL_LEN: int = 255
CELL_LEN: int = 13
API_KEY_LEN: int = 64


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

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

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

    async def update_rate_limits_from_plan(self, plan_data: dict[str, str | bool | int]) -> Self:
        """

        :param plan_data:
        :return:
        """
        self.rate_limit = plan_data.get("rate_limit")
        self.duration = 60 * 60 * 1  # ONE hOUR FOR ALL PLANS
        self.subscription.api_requests_balance = plan_data.get("plan_limit")
        return self

    @classmethod
    async def get_all_active(cls, session: sessionType):
        return session.query(cls).filter_by(is_active=True).all()


async def cache_api_keys() -> int:
    with next(sessions) as session:
        db_keys = await ApiKeyModel.get_all_active(session=session)
        async with apikeys_lock:
            api_keys.update({db_key.api_key: {'requests_count': 0,
                                              'last_request_timestamp': 0,
                                              'duration': db_key.duration,
                                              'rate_limit': db_key.rate_limit} for db_key in db_keys})
    return len(db_keys)
#
# async def create_admin_key():
#     """
#         this is only for the purposes of testing
#     :return:
#     """
#     from src.database.account.account import Account
#     with next(sessions) as session:
#
#         _uuid = create_id(size=UUID_LEN)
#         _api_key = create_id(size=UUID_LEN)
#         first_name = "John"
#         second_name = "Peters"
#         surname = "Smith"
#         email = "info@eod-stock-api.site"
#         cell = "0711863234"
#         is_admin = True
#         admin_user = Account(uuid=_uuid, first_name=first_name,
#                              second_name=second_name, surname=surname, email=email,
#                              cell=cell, is_admin=is_admin, password="MobiusCrypt5627084@")
#
#         api_key = ApiKeyModel(uuid=_uuid,
#                               api_key=_api_key,
#                               duration=ONE_MINUTE * 60,
#                               rate_limit=30,
#                               is_active=True)
#
#         sub_id = create_id(UUID_LEN)
#         # await create_plans()
#         plans = await Plans.get_all_plans(session=session)
#         _enterprise_plan: Plans = [plan for plan in plans if plan.plan_name == "ENTERPRISE"][0]
#         subscription = Subscriptions(uuid=_uuid, subscription_id=sub_id, plan_id=_enterprise_plan.plan_id,
#                                      time_subscribed=datetime.datetime.now().timestamp(), payment_day="31",
#                                      api_requests_balance=_enterprise_plan.plan_limit)
#         try:
#             session.add(admin_user)
#             session.commit()
#             session.flush()
#             session.add(subscription)
#             session.add(api_key)
#             session.commit()
#             session.flush()
#
#         except pymysql.err.OperationalError as e:
#             # TODO log errors
#             pass
