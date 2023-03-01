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


async def send_invoice(args: dict[str, dict[str, str | int]]) -> None:
    """
    **send_invoice**
        :param args:
        :return:
    """
    invoice: dict[str, str | int] = args.get("invoice", {})
    account: dict[str, str | int] = args.get("account", {})

    if invoice and account:
        pass
    # TODO  Compile and Email and then send to client here


async def add_invoice_to_send(invoice: dict[str, str | int], account: dict[str, str | int]):
    """
    **add_invoice_to_send**

    :return: None
    """
    _account = await get_account_details(account=account)
    add_argument(dict(account=_account, invoice=invoice))


async def get_account_details(account: dict[str, str | int]) -> dict[str, str | int]:
    """select relevant fields from account dict"""
    email = account.get("email")
    cell = account.get("cell")
    first_name = account.get("first_name")
    second_name = account.get("second_name")
    surname = account.get("surname")
    return dict(cell=cell, email=email, first_name=first_name, second_name=second_name, surname=surname)
