from src.config import config_instance
from CloudFlare import CloudFlare
import ipaddress

EMAIL = config_instance().CLOUDFLARE_SETTINGS.EMAIL
TOKEN = config_instance().CLOUDFLARE_SETTINGS.TOKEN


# Create a middleware function that checks the IP address of incoming requests and only allows requests from the
# Cloudflare IP ranges. Here's an example of how you could do this:

class CloudFlareFirewall:
    """
        TODO add more functionality to further enhance the security of our gateway
    """
    def __init__(self):
        self.cloud_flare = CloudFlare(email=EMAIL, token=TOKEN)
        self.ip_ranges = ['173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22', '141.101.64.0/18',
                          '108.162.192.0/18', '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22',
                          '198.41.128.0/17',
                          '162.158.0.0/15', '104.16.0.0/13', '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22']

    async def check_ip_range(self, ip):
        for ip_range in self.ip_ranges:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(ip_range):
                return True
        return False
