from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()


class PayPalIPN(BaseModel):
    """
    Model to handle data from PayPal IPN
    """
    txn_id: str
    txn_type: str
    payment_status: str
    mc_gross: float
    mc_currency: str
    custom: str
