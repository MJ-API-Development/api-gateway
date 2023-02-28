"""
    invoice queues
"""
from typing import Callable
import asyncio

_outgoing_invoices_queues: list[dict[str, str | int]] = list()
get_argument: Callable = _outgoing_invoices_queues.pop
add_argument: Callable = _outgoing_invoices_queues.append


async def process_invoice_queues():
    """
    **process_queues**

    :return:
    """
    while True:
        if _outgoing_invoices_queues:
            await send_invoice(args=get_argument())
            # sleep for 1 minute
        await asyncio.sleep(60 * 1)


async def send_invoice(args: dict[str, str | int, dict[str, str | int]]) -> None:
    """
    **send_invoice**
        :param args:
        :return:
    """
    pass


async def add_invoice_to_send(invoice: dict, account: dict):
    """
    **add_invoice_to_send**

    :return: None
    """
    email = account.get("email")
    cell = account.get("cell")
    add_argument(dict(email=email, cell=cell, invoice=invoice))

