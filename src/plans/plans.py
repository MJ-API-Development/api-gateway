from enum import Enum
from typing import Self

from numba import jit
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.apikeys.keys import Base, sessionType
from src.const import UUID_LEN, NAME_LEN


class Subscriptions(Base):
    __tablename__ = "subscriptions"
    subscription_id: str = Column(String(UUID_LEN), primary_key=True)
    uuid: str = Column(String(UUID_LEN), ForeignKey("eod_api_keys.uuid"))
    plan_id: str = Column(String(UUID_LEN), ForeignKey("plans.plan_id"))
    time_subscribed: float = Column(Float)
    payment_day: str = Column(String(NAME_LEN))
    _is_active: bool = Column(Boolean)
    api_requests_balance: int = Column(Integer)

    def to_dict(self):
        return {
            "subscription_id": self.subscription_id,
            "uuid": self.uuid,
            "plan_id": self.plan_id,
            "time_subscribed": self.time_subscribed,
            "payment_day": self.payment_day,
            "is_active": self._is_active,
            "api_requests_balance": self.api_requests_balance
        }

    async def is_active(self, session: sessionType):
        """

            Subscription is Active if _is_active is True, and plan fully paid
            NOTE: there maybe other reasons to turn off subscriptions other than payments
        :return:
        """
        invoices = session.query(Invoices).filter(Invoices.subscription_id == self.subscription_id).all()
        for invoice in invoices:
            if not invoice.is_paid(session=session):
                return False
        return self._is_active

    async def can_access_resource(self, resource_name: str, session: sessionType) -> bool:
        """
            with a resource name checks if it can be accessed
            by the subscribed plan
        :param resource_name:
        :param session:
        :return:
        """
        return session.query(Plans).filter(
            Plans.plan_id == self.plan_id).first().resource_exist(resource_name=resource_name)


class PlanType(Enum):
    hard_limit: str = "hard_limit"
    soft_limit: str = "soft_limit"


class Plans(Base):
    """
        Subscription Plans
    """
    __tablename__ = "plans"
    plan_id: str = Column(String(UUID_LEN), primary_key=True, index=True)
    plan_name: str = Column(String(NAME_LEN), index=True, unique=True)
    charge_amount: int = Column(Integer)  # Payment Amount for this plan in Cents
    description: str = Column(Text)
    _resource_str: str = Column(Text)
    rate_limit: int = Column(Integer)  # Limit per Hour
    plan_limit: int = Column(Integer)  # Monthly Limit
    plan_limit_type: PlanType = Column(String(10))  # Hard or Soft Limit
    rate_per_request: int = Column(Integer, default=0)  # in Cents
    subscriptions = relationship("Subscriptions", uselist=True, foreign_keys=[Subscriptions.plan_id])

    @property
    def resource_set(self) -> set[str]:
        return {res.lower() for res in self._resource_str.split(",")}

    @resource_set.setter
    def resource_set(self, rs_set: set[str]):
        self._resource_str = ",".join(rs_set)

    def to_dict(self) -> dict[str, str | int | set[str]]:
        return {
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "Amount": self.charge_amount,
            "description": self.description,
            "resources": self.resource_set,
            "rate_limit": self.rate_limit,
            "plan_limit": self.plan_limit,
            "plan_limit_type": self.plan_limit_type,
            "rate_per_request": self.rate_per_request,
        }

    @jit
    def resource_exist(self, resource_name: str) -> bool:
        """

        :param resource_name:
        :return:
        """
        return resource_name in self.resource_set

    @classmethod
    async def get_plan_by_plan_id(cls, plan_id: str, session: sessionType) -> Self:
        """
            given plan_id will return subscribed Plan
        :param session:
        :param plan_id:
        :return:
        """
        return session.query(cls).filter(cls.plan_id == plan_id).first()

    def is_hard_limit(self) -> bool:
        return self.plan_limit_type == PlanType.hard_limit


class Payments(Base):
    """
        subscription_id , links to the subscription being paid for
        payment_method, indicates the method used for payments
        is_success, will be true if payment is successful
        time_paid, time payment was made
        period_paid, the term in number days the plan was paid for, this is pre paid
    """
    __tablename__ = "payments"
    subscription_id: str = Column(String(UUID_LEN), ForeignKey("subscriptions.subscription_id"))
    payment_id: str = Column(String(UUID_LEN), primary_key=True)
    invoice_id: str = Column(String(UUID_LEN), ForeignKey("invoices.invoice_id"))
    payment_method: str = Column(String(NAME_LEN))
    payment_amount: int = Column(Integer)  # amount in cents
    is_success: bool = Column(Boolean)
    time_paid: float = Column(Float)


class Invoices(Base):
    __tablename__ = "invoices"
    invoice_id: str = Column(String(UUID_LEN), primary_key=True)
    subscription_id: str = Column(String(UUID_LEN), ForeignKey("subscriptions.subscription_id"))
    invoiced_amount: int = Column(Integer)
    invoice_from_date: float = Column(Float)
    invoice_to_date: float = Column(Float)
    time_issued: float = Column(Float)

    def to_dict(self) -> dict[str, str | int | float]:
        """

        :return:
        """
        return {
            "invoice_id": self.invoice_id,
            "subscription_id": self.subscription_id,
            "invoiced_amount": self.invoiced_amount,
            "invoice_from_date": self.invoice_from_date,
            "invoice_to_date": self.invoice_to_date,
            "time_issued": self.time_issued
        }

    def is_paid(self, session: sessionType) -> bool:
        """
            call to learn if an invoice is paid
        :param session:
        :return:
        """
        return session.query(Payments).filter(Payments.invoice_id == self.invoice_id).filter(
            Payments.payment_amount >= self.invoiced_amount).first() is not None
