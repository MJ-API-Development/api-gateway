import aiohttp

from src.config import config_instance


async def verify_ipn(ipn_data):
    """
    Verify that an IPN is valid by sending it back to PayPal.

    :param ipn_data: The IPN data received from PayPal.
    :return: The response from PayPal ("VERIFIED" or "INVALID").
    """
    PAYPAL_VERIFY_URL = "https://ipnpb.paypal.com/cgi-bin/webscr"
    PAYPAL_TOKEN = f"Bearer {config_instance().PAYPAL_SETTINGS.BEARER_TOKEN}"
    # Add 'cmd=_notify-validate' parameter for verification
    ipn_data["cmd"] = "_notify-validate"
    header = {'Authentication': PAYPAL_TOKEN}
    # TODO there are some additional information i need to include on the IPN verification
    async with aiohttp.ClientSession() as session:
        async with session.post(url=PAYPAL_VERIFY_URL, json=ipn_data, headers=header) as resp:
            return await resp.text()
