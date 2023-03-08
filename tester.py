import ipaddress
import re
# Define the list of IP ranges
ip_ranges = ['173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22', '141.101.64.0/18',
             '108.162.192.0/18', '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22', '198.41.128.0/17',
             '162.158.0.0/15', '104.16.0.0/13', '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22']


# Function to check if an IP address falls within one of the IPV4 ranges
def check_ip_range(path: str):
    print(re.match(pattern="^/api/v1/exchanges/$", string="/api/v1/exchanges/"))


if __name__ == '__main__':
    check_ip_range("/api/v1/exchanges")
