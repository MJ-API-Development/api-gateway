"""
    invoice queues
"""

outgoing_invoices_queues: list[dict[str, str | int]] = list()


async def process_queues():
    """
    **process_queues**

    :return:
    """
    while True:
        if outgoing_invoices_queues:
            args = outgoing_invoices_queues.pop()
            await send_invoice(args=args)


async def send_invoice(args: dict[str, str | int]):
    """
    **send_invoice**
        :param args:
        :return:
    """
    pass
