import ipaddress
import re
import time

from cryptography.fernet import Fernet

# Define the list of IP ranges
ip_ranges = ['173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22', '141.101.64.0/18',
             '108.162.192.0/18', '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22', '198.41.128.0/17',
             '162.158.0.0/15', '104.16.0.0/13', '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22']


# Function to check if an IP address falls within one of the IPV4 ranges
def output(*args, **kwargs):
    print(f"{args=}")
    print(f"{kwargs=}")


key = b'tZThIdlfwhN_hzrPKE11d4wFwHfAPSYhjG3tVl2oV_E='
if __name__ == '__main__':
    # print(Fernet.generate_key())
    # b'gAAAAABkDWaK_aUP9HwAEoxC6J0dd2hYH9cjaowSHKrPWs9pZWlFikAVkMNqi8XwzEzLbRIBkPm7IqvP9XxdG5N2TfHwTPU5NA=='

    _plain = "text to encrypt"
    encrypted_text = Fernet(key).encrypt(data=_plain.encode('utf-8'))
    print(encrypted_text)
    time.sleep(1)
    print(Fernet(key=key).decrypt(token=encrypted_text).decode('utf-8'))
    my_tuple = (1, 2, 3)
    my_dict = {'one': 1, 'two': 2}
    output(my_tuple, **my_dict)
