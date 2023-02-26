from sqlalchemy import Column, String, Text, Integer, Date, Float, Boolean, ForeignKey

from src.apikeys.keys import Base, sessionType
from src.const import UUID_LEN, NAME_LEN
from numba import jit


class Plans(Base):
    __tablename__ = "plans"
    plan_id: str = Column(String(UUID_LEN), primary_key=True, index=True)
    plan_name: str = Column(String(NAME_LEN), index=True, unique=True)
    charge_amount: int = Column(Integer)  # Payment Amount for this plan in Cents
    description: str = Column(Text)
    _resource_str: str = Column(Text)
    rate_limit: int = Column(Integer)
    plan_limit: int = Column(Integer)
    plan_limit_type: int = Column(String(8))  # Hard or Soft Limit
    rate_per_request: int = Column(Integer)  # in Cents

    @property
    def resource_set(self) -> set[str]:
        return set([res.lower() for res in self._resource_str.split(",")])

    @resource_set.setter
    def resource_set(self, rs_set: set[str]):
        self._resource_str = ",".join(rs_set)

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "subscription_id": self.subscription_id,
            "screen_name": self.screen_name,
            "plan": self.plan,
            "resources": self.resource_list
        }

    @jit
    def resource_exist(self, resource_path: str) -> bool:
        """

        :param resource_path:
        :return:
        """
        _resource_path = resource_path.lower()
        return _resource_path in self.resource_set


class Subscriptions(Base):
    __tablename__ = "subscriptions"
    subscription_id: str = Column(String(UUID_LEN), primary_key=True)
    uuid: str = Column(String(UUID_LEN), ForeignKey("eod_api_keys.uuid"))
    plan_id: str = Column(String(UUID_LEN), ForeignKey("plans.plan_id"))
    time_subscribed: float = Column(Float)
    payment_day: str = Column(String(NAME_LEN))
    _is_active: bool = Column(Boolean)

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

    async def can_access_resource(self, resource_path: str, session: sessionType) -> bool:
        """

        :param resource_path:
        :param session:
        :return:
        """
        return session.query(Plans).filter(
            Plans.plan_id == self.plan_id).first().resource_exist(resource_path=resource_path)


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

    def is_paid(self, session: sessionType) -> bool:
        """
            call to learn if an invoice is paid
        :param session:
        :return:
        """
        return session.query(Payments).filter(Payments.invoice_id == self.invoice_id).filter(
            Payments.payment_amount >= self.invoiced_amount).first() is not None
