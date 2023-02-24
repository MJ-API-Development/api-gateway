"""
    **Module Utils**
     - Common Application Utilities**
     - Utilities for commonly performed tasks -
"""
__developer__ = "mobius-crypt"
__email__ = "mobiusndou@gmail.com"
__twitter__ = "@blueitserver"
__github_profile__ = "https://github.com/freelancing-solutions/"

import datetime
import os
import random
import string
import time
from datetime import date
from datetime import time as time_class
from functools import wraps
from typing import Callable, List, Optional, Union
from numba import jit
from src.config import config_instance

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


# Creates an ID for use as a unique ID
# noinspection PyArgumentList
@jit
def create_id(size: int = 16, chars: str = _char_set) -> str:
    """
        **create_id**
            create a random unique id for use as indexes in Database Models

    :param size: size of string - leave as default if you can
    :param chars: character set to create Unique identifier from leave as default
    :return: uuid -> randomly generated id
    """
    return ''.join(random.choice(chars) for _ in range(size))

@jit
def is_valid_chars(value: str, chars: str = _input_character_set) -> bool:
    """
        **is_valid_chars**
            checks if all characters are valid

    :param value: value to check
    :param chars: valid characters
    :return: bool indicating if characters are valid or not
    """
    return not bool([invalid_char for invalid_char in value if invalid_char not in chars])

def end_of_month() -> bool:
    """
        **end_of_month**
            True if the present date can be considered end of month or near end of month
        :return boolean -> True if end of month
    """
    return today().day in [30, 31, 1]


# Used to control cache ttl
def return_ttl(name: str) -> int:
    """
        **return_ttl**
            returns ttl for cache depending on long, short, and medium

    :param name: string -> period = short, medium, long
    :return: int -> time to live
    """
    cache_ttl_short: int = 1800  # (60*60 * 0.5) 30 minutes
    cache_ttl_medium: int = 3600  # (60 * 60) 1 hour
    cache_ttl_long: int = 5400  # (60 * 60 * 1.5) 1 hour 30 minutes

    if name == "long":
        return cache_ttl_long
    elif name == "short":
        return cache_ttl_short
    elif name == "medium":
        return cache_ttl_medium
    return cache_ttl_short


def today() -> date:
    """
    **today**
        returns today's date

    :return present date
    """
    return datetime.datetime.now().date()


def time_now() -> time_class:
    """
        **time_now**
            NOTE: Returns the present time
        :return present time
    """
    return datetime.datetime.now().time()


def datetime_now() -> datetime:
    """
        **datetime_now**
            NOTE: Returns the present datetime
        :return: present datetime
    """
    return datetime.datetime.now()


def date_days_ago(days: int) -> date:
    """
        **date_days_ago**
            NOTE: returns a date indicated by days in the past

        :param days -> int number of days to go backwards
        :return previous date counted by days before
    """
    return (datetime.datetime.now() - datetime.timedelta(days=days)).date()

@jit
def camel_to_snake(name: str) -> str:
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


if __name__ == '__main__':
    pass
