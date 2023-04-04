from pydantic import BaseModel



class PayPalIPN(BaseModel):
    """
    Model to handle data from PayPal IPN
    """
    txn_id: str | None
    txn_type: str | None
    payment_status: str | None
    mc_gross: float | None
    mc_currency: str | None
    custom: str | None
