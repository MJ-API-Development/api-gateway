from pydantic import BaseModel
from src.management_api.models.subscriptions import SubscriptionUpdate


class ApiKeysModel(BaseModel):
    uuid: str
    api_key: str
    duration: int
    rate_limit: int
    is_active: bool
    subscription: SubscriptionUpdate
