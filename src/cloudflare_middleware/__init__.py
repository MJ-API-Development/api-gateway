from src.config import config_instance
from CloudFlare import CloudFlare


EMAIL = config_instance().CLOUDFLARE_SETTINGS.EMAIL
TOKEN = config_instance().CLOUDFLARE_SETTINGS.TOKEN


# Create a middleware function that checks the IP address of incoming requests and only allows requests from the
# Cloudflare IP ranges. Here's an example of how you could do this:

class CloudFlareFirewall:
    def __init__(self):
        self.cloud_flare = CloudFlare(email=EMAIL, token=TOKEN)

    def cloudflare_ips(self) -> list[str]:
        ip_list = self.cloud_flare.zones.firewall.access_rules.rules(ip_firewall=True)
        return [rule['configuration']['value'] for rule in ip_list]
