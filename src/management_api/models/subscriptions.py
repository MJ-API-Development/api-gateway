from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    """
        BaseClass for creating New Subscriptions
    """
    plan_id: str
    uuid: str
    payment_method: str


class SubscriptionUpdate(BaseModel):
    subscription_id: str
    plan_id: str
    uuid: str | None = None
    time_subscribed: float | None = None
    payment_day: str | None = None
    _is_active: bool | None = None
    api_requests_balance: int | None = None
    approval_url: str | None = None
    paypal_id: str | None = None


