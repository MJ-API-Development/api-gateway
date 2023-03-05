"""
    **Module Utils**
     - Common Application Utilities**
     - Utilities for commonly performed tasks -
"""
__developer__ = "mobius-crypt"
__email__ = "mobiusndou@gmail.com"
__twitter__ = "@blueitserver"
__github_profile__ = "https://github.com/freelancing-solutions/"

import random
import re
import string
import time
from datetime import date
from functools import wraps
from numba import jit

# NOTE set of characters to use when generating Unique ID
_char_set = string.ascii_lowercase + string.ascii_uppercase + string.digits

# NOTE input character set
_input_character_set = string.printable


def _retry(delay: int = 3, exception: Exception = None):
    # noinspection PyBroadException
    def decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            tries = 0
            while tries < 3:
                try:
                    return func(*args, **kwargs)
                except exception:
                    time.sleep(delay * 2 ** tries)
                    tries += 1
            raise exception

        return wrapped_function

    return decorator


def calculate_invoice_date_range(today: float) -> tuple[float, float]:
    """

    :param today:
    :return:
    """
    pass


# Creates an ID for use as a unique ID
# noinspection PyArgumentList
@jit(forceobj=True)
def create_id(size: int = 16, chars: str = _char_set) -> str:
    """
        **create_id**
            create a random unique id for use as indexes in Database Models

    :param size: size of string - leave as default if you can
    :param chars: character set to create Unique identifier from leave as default
    :return: uuid -> randomly generated id
    """
    return ''.join(random.choices(chars, k=size))


@jit(forceobj=True)
def camel_to_snake(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


@jit(forceobj=True)
def create_api_key() -> str:
    return f"{create_id(6)}-{create_id(4)}-{create_id(4)}-{create_id(4)}-{create_id(12)}"


if __name__ == '__main__':
    pass
