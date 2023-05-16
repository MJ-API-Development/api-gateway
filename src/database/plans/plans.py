import datetime

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, inspect
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import relationship
from typing_extensions import Self

from src.const import UUID_LEN, NAME_LEN
from src.database.database_sessions import sessionType, Base, engine
from src.utils.utils import create_id


class Subscriptions(Base):
    __tablename__ = "subscriptions"
    subscription_id: str = Column(String(UUID_LEN), primary_key=True)
    uuid: str = Column(String(UUID_LEN), ForeignKey("eod_api_keys.uuid"))
    plan_id: str = Column(String(UUID_LEN), ForeignKey("plans.plan_id"))
    time_subscribed: float = Column(Float)
    payment_day: str = Column(String(NAME_LEN))
    _is_active: bool = Column(Boolean, default=False)
    api_requests_balance: int = Column(Integer)

    approval_url: str = Column(String(255))
    paypal_id: str = Column(String(255))

    def __init__(self, subscription_id: str, uuid: str, plan_id: str, time_subscribed: float, payment_day: str,
                 api_requests_balance: int, approval_url: str, paypal_id: str, is_active: bool = False):
        """

        :param subscription_id:
        :param uuid:
        :param plan_id:
        :param time_subscribed:
        :param payment_day:
        :param api_requests_balance:
        :param approval_url:
        :param paypal_id:
        :param is_active:
        """
        self.subscription_id = subscription_id
        self.uuid = uuid
        self.plan_id = plan_id
        self.time_subscribed = time_subscribed
        self.payment_day = payment_day
        self.api_requests_balance = api_requests_balance
        self.approval_url = approval_url
        self.paypal_id = paypal_id
        self._is_active = is_active

    def set_is_active(self, is_active: bool):
        """
            **set_is_active**
                used to activate or de-activate subscription
        :return:
        """
        self._is_active = is_active

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    def to_dict(self) -> dict[str, str | float | int | bool]:
        return {
            "subscription_id": self.subscription_id,
            "uuid": self.uuid,
            "plan_id": self.plan_id,
            "time_subscribed": self.time_subscribed,
            "payment_day": self.payment_day,
            "is_active": self._is_active,
            "api_requests_balance": self.api_requests_balance
        }

    async def is_active(self, session: sessionType) -> bool:
        """

            Subscription is Active if _is_active is True, and plan fully paid
            NOTE: there maybe other reasons to turn off subscriptions other than payments
        :return:
        """
        invoices = session.query(Invoices).filter(Invoices.subscription_id == self.subscription_id).all()
        return False if any([invoice for invoice in invoices
                             if not invoice.is_paid(session=session)]) else self._is_active

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

    @classmethod
    async def create_subscription(cls, _data: dict[str, str | bool | int], session: sessionType) -> Self:
        """
            Will create a subscription instance and then return
            return True
        :param session:
        :param _data:
        :return:
        """
        instance = cls(**_data)
        return instance

    @classmethod
    async def activate(cls, subscription_id: str, session: sessionType) -> bool:
        """

        :param session:
        :param subscription_id:
        :return: 
        """
        subscription = session.query(cls).filter(cls.subscription_id == subscription_id).first()
        subscription._is_active = True
        session.merge(subscription)
        session.commit()

    @classmethod
    async def get_by_subscription_id(cls, subscription_id: str, session: sessionType) -> Self:
        """
            :param subscription_id:
            :param session:
            :return: Self
        """
        return session.query(cls).filter(cls.subscription_id == subscription_id).first()

    @classmethod
    async def update_subscription(cls, subscription_data: dict[str, str | bool | int], session: sessionType) -> bool:
        api_key = subscription_data.pop('api_key', None)
        if not api_key:
            return False  # no api_key provided, can't update

        try:
            subscription = session.query(cls).filter_by(uuid=api_key).one()
        except NoResultFound:
            return False  # subscription not found for this api_key

        # update only the fields that exist on the subscription_data dictionary
        for field, value in subscription_data.items():
            if hasattr(subscription, field):
                setattr(subscription, field, value)

        session.merge(subscription)
        session.commit()
        return True  # update successful


class PlanType:
    hard_limit: str = "hard_limit"
    soft_limit: str = "soft_limit"


class Plans(Base):
    """
        Subscription Plans
    """
    __tablename__ = "plans"
    plan_id: str = Column(String(UUID_LEN), primary_key=True, index=True)
    paypal_id: str = Column(String(255), index=True)
    plan_name: str = Column(String(NAME_LEN), index=True, unique=True)
    charge_amount: int = Column(Integer)  # Payment Amount for this plan in Cents
    description: str = Column(Text)
    _resource_str: str = Column(Text)
    rate_limit: int = Column(Integer)  # Limit per Hour
    plan_limit: int = Column(Integer)  # Monthly Limit
    plan_limit_type: PlanType = Column(String(10))  # Hard or Soft Limit
    rate_per_request: int = Column(Integer, default=0)  # in Cents
    is_visible: bool = Column(Boolean, default=True)  # Only visible plans are shown in the interface
    subscriptions = relationship("Subscriptions", uselist=True, foreign_keys=[Subscriptions.plan_id])

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @property
    def resource_set(self) -> set[str]:
        return set([res.lower() for res in self._resource_str.split(",")])

    @resource_set.setter
    def resource_set(self, rs_set: set[str]):
        self._resource_str = ",".join(rs_set)

    def to_dict(self) -> dict[str, str | int | set[str]]:
        return {
            "plan_id": self.plan_id,
            "paypal_id": self.paypal_id,
            "plan_name": self.plan_name,
            "Amount": self.charge_amount,
            "description": self.description,
            "resources": list(self.resource_set),
            "rate_limit": self.rate_limit,
            "plan_limit": self.plan_limit,
            "plan_limit_type": self.plan_limit_type,
            "rate_per_request": self.rate_per_request,
        }

    def resource_exist(self, resource_name: str) -> bool:
        """
            **resource_exist**
                checks if a specific resource exist on client plan
        :param resource_name:
        :return:
        """
        # TODO Upgrade this on database
        _new_resources = ["news.articles.paged"]
        if resource_name in _new_resources:
            return True
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

    @classmethod
    async def get_all_plans(cls, session: sessionType) -> list[Self]:
        """

        :param session:
        :return:
        """
        return session.query(cls).all()

    def is_hard_limit(self) -> bool:
        return self.plan_limit_type == PlanType.hard_limit

    @classmethod
    def fetch_all(cls, session: sessionType):
        return session.query(cls).all()


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

    def __init__(self, subscription_id: str, payment_method: str, payment_amount: int, is_success: bool = True,
                 invoice_id: str = None, payment_id: str = None):

        self.subscription_id = subscription_id
        self.payment_method = payment_method
        self.payment_amount = payment_amount
        self.is_success = is_success
        self.time_paid = datetime.datetime.now().timestamp()
        self.invoice_id = invoice_id or create_id()
        self.payment_id = payment_id or create_id()

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    def to_dict(self) -> dict[str, str | int | float]:
        """
        :return:
        """
        return {
            "subscription_id": self.subscription_id,
            "payment_id": self.payment_id,
            "invoice_id": self.invoice_id,
            "payment_method": self.payment_method,
            "payment_amount": self.payment_amount,
            "is_success": self.is_success,
            "time_paid": self.time_paid
        }

    async def on_payment(self, _data: dict[str, str | int], session: sessionType):
        """
            on payment notification
                notifications will be sent by the payment gateway
                verify payment and then activate subscription

        :param session:
        :param _data:
        :return:
        """
        if await self.verify_payment(_data=_data, session=session):
            await Subscriptions.activate(self.subscription_id, session=session)

    async def verify_payment(self, _data: dict[str, str | int | bool], session: sessionType):
        """
        **verify payment **
            this method will be dependent on the payment method used to process payment
            once payment is verified success will be set to true
            payment amount rechecked, and time_paid adjusted to match receipt data
        :param session:
        :param _data:
        :return:
        """
        pass


class Invoices(Base):
    """
        Invoices
        param:
        invoice_uri: will be used in payments to locate the invoice
    """
    __tablename__ = "invoices"
    invoice_id: str = Column(String(UUID_LEN), primary_key=True)
    subscription_id: str = Column(String(UUID_LEN), ForeignKey("subscriptions.subscription_id"))
    invoiced_amount: int = Column(Integer)
    invoice_from_date: float = Column(Float)
    invoice_to_date: float = Column(Float)
    time_issued: float = Column(Float)
    invoice_uri: str = Column(String(255))

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

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

    @classmethod
    async def create_invoice(cls, _data: dict[str, str | int | bool], session: sessionType) -> Self:
        """
            **create_invoice**
                given subscription data create an invoice and send to
                client with email.

                wait for payment notification then activate subscription upon receipt of
                payment
        :param session:
        :param _data:
        :return: True if invoice was created and scheduled to be sent
        """
        pass
