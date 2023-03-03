import aiohttp


async def verify_ipn(ipn_data):
    """
    Verify that an IPN is valid by sending it back to PayPal.

    :param ipn_data: The IPN data received from PayPal.
    :return: The response from PayPal ("VERIFIED" or "INVALID").
    """
    PAYPAL_VERIFY_URL = "https://ipnpb.paypal.com/cgi-bin/webscr"

    # Add 'cmd=_notify-validate' parameter for verification
    ipn_data["cmd"] = "_notify-validate"

    async with aiohttp.ClientSession() as session:
        async with session.post(PAYPAL_VERIFY_URL, data=ipn_data) as resp:
            return await resp.text()
