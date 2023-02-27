import functools
import threading
import time
from json import JSONDecodeError
from typing import Any

import redis
import ujson
from numba import int32, float32
from redis import ConnectionError

from src.config import config_instance
from src.utils.my_logger import init_logger
from src.utils.utils import camel_to_snake

MEM_CACHE_SIZE = config_instance().CACHE_SETTINGS.MAX_CACHE_SIZE
EXPIRATION_TIME = config_instance().CACHE_SETTINGS.CACHE_DEFAULT_TIMEOUT
spec = [
    ('value', int32),  # a simple scalar field
    ('array', float32[:]),  # an array field
]


class Cache:
    """
        A class to handle caching of data, both in-memory and in Redis.
        The class provides thread-safe caching and automatic cache eviction when full.

        :param max_size: The maximum size of the in-memory cache. The default is set in the config file.
        :param expiration_time: The expiration time of each cache entry, in seconds. The default is set in the config
                file.
        :param use_redis: Indicates whether to use a Redis cache. The default is False.
    """

    def __init__(self, cache_name: str = "mem", max_size: int = MEM_CACHE_SIZE, expiration_time: int = EXPIRATION_TIME,
                 use_redis: bool = False):
        """
            Initializes the cache and creates a redis client if use_redis=True.
            IF Redis fails the cache will fall back to using in Memory Cache
        """
        self.max_size = max_size
        self.expiration_time = expiration_time
        self._cache_name = cache_name
        self._cache = {}
        self._lock = threading.Lock()
        self._use_redis = use_redis
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))
        if self._use_redis:
            redis_host = config_instance().REDIS_CACHE.CACHE_REDIS_HOST
            redis_port = config_instance().REDIS_CACHE.CACHE_REDIS_PORT
            password = config_instance().REDIS_CACHE.REDIS_PASSWORD
            # Azure Redis not using username, may use it in the future in case we are changing to another redis client
            # or using multiple redis clients at the same time
            # noinspection PyUnusedLocal
            username = config_instance().REDIS_CACHE.REDIS_USERNAME
            try:
                self._redis_client = redis.StrictRedis(host=redis_host, port=redis_port, password=password)
                self._redis_client.flushall(asynchronous=True)
                # self._redis_client = redis.Redis(host=redis_host, port=redis_port, username=username, password=password)
                config_instance().DEBUG and self._logger.info("Using Redis -- Connection Successful")
            except ConnectionError:
                config_instance().DEBUG and self._logger.error(msg="Redis failed to connect....")
                self.turn_off_redis()

    @property
    def can_use_redis(self):
        return self._use_redis

    def turn_off_redis(self):
        self._use_redis = False

    def on_delete(self):
        """
            run when you need to delete all keys
        :return:
        """
        try:
            self._redis_client.flushall(asynchronous=True)
        except ConnectionError:
            config_instance().DEBUG and self._logger.error(msg="Redis failed to connect....")
            # self.turn_off_redis()

    def _serialize_value(self, value: Any) -> str:
        """
            Serialize the given value to a json string.
        """
        try:
            return ujson.dumps(value)
        except JSONDecodeError as e:
            config_instance().DEBUG and self._logger.error(f"Could be bad data on input stream {str(e)}")
            return value
        except TypeError as e:
            config_instance().DEBUG and self._logger.error(f"Could be bad data on input stream {str(e)}")
            return value

    def _deserialize_value(self, value: any) -> Any:
        """
            Deserialize the given json string to a python object.
        """
        try:
            return ujson.loads(value)
        except JSONDecodeError as e:
            config_instance().DEBUG and self._logger.error(f"Could be bad data on output stream {str(e)}")
            return value
        except TypeError as e:
            config_instance().DEBUG and self._logger.error(f"Could be bad data on output stream {str(e)}")
            return value

    def set(self, key: str, value: Any, expiration_time: int = 0):
        """
            Store the value in the cache. If the key already exists, the value is updated.
            If use_redis=True the value is stored in Redis, otherwise it is stored in-memory
        """
        value = self._serialize_value(value)
        if self._use_redis:
            exp_time = expiration_time if expiration_time else self.expiration_time
            self._redis_client.set(key, value, ex=exp_time)
        else:
            with self._lock:
                # If the cache is full, remove the oldest entry
                if len(self._cache) >= self.max_size:
                    self._remove_oldest_entry()
                # Add the new entry
                self._cache[key] = {'value': value, 'timestamp': time.time()}

    def get(self, key: str) -> Any:
        """
            Retrieve the value associated with the given key. If use_redis=True
            the value is retrieved from Redis, otherwise it is retrieved from in-memory cache.
        """
        if self._use_redis:
            try:
                value = self._redis_client.get(key)
            except redis.exceptions.TimeoutError:
                config_instance().DEBUG and self._logger.error("Timeout Error Reading from redis")
                value = None
            except redis.exceptions.ConnectionError:
                config_instance().DEBUG and self._logger.error("ConnectionError Reading from redis")
                value = None

        else:
            with self._lock:
                # Return the value if it's in the cache and hasn't expired
                entry = self._cache.get(key)
                if entry and time.time() - entry['timestamp'] < self.expiration_time:
                    value = entry['value']
                else:
                    value = None

        return self._deserialize_value(value)

    def _remove_oldest_entry(self):
        """
             Remove the oldest entry in the in-memory cache.
        :return:
        """
        with self._lock:
            # Find the oldest entry
            oldest_entry = None
            for key, value in self._cache.items():
                if oldest_entry is None:
                    oldest_entry = key
                elif value['timestamp'] < self._cache[oldest_entry]['timestamp']:
                    oldest_entry = key

            # Remove the oldest entry
            if oldest_entry is not None:
                self._cache.pop(oldest_entry)

    def delete_redis_key(self, key):
        self._redis_client.delete(key)

    def clear_mem_cache(self):
        self._cache = {}


def create_key(method: str, kwargs: dict[str, str | int]) -> str:
    """
        used to create keys for cache redis handler
    """
    if not kwargs:
        _key = "all"
    else:
        _key = ".".join(f"{key}={str(value)}" for key, value in kwargs.items() if value).lower()
    return f"{method}.{_key}"


def cached(func):
    async def wrapper(*args, **kwargs):
        new_kwargs = kwargs.copy()
        for key, value in kwargs.items():
            if key == 'session':
                # removing session from keys
                _ = new_kwargs.pop(key)

        _key = create_key(method=func.__name__, kwargs=new_kwargs)
        _data = mem_cache.get(_key)
        if _data is None:
            result = await func(*args, **kwargs)
            if result:
                mem_cache.set(key=_key, value=_data, expiration_time=60 * 60 * 1)
                # redis_cache.set(key=_key, value=result, expiration_time=60*60*1)
            return result
        return _data

    return wrapper


def cached_ttl(ttl: int = 60 * 60 * 1):
    def _cached(func):
        async def _wrapper(*args, **kwargs):
            new_kwargs = kwargs.copy()
            for key, value in kwargs.items():
                if key == 'session':
                    # removing session from keys
                    _ = new_kwargs.pop(key)

            _key = create_key(method=func.__name__, kwargs=new_kwargs)
            _data = mem_cache.get(_key)
            if _data is None:
                result = await func(*args, **kwargs)
                if result:
                    mem_cache.set(key=_key, value=_data, expiration_time=ttl)
                    # redis_cache.set(key=_key, value=result, expiration_time=60*60*1)
                return result
            return _data

        return _wrapper

    return _cached


# Set Use redis to false temporarily

redis_cache = Cache(cache_name="redis", use_redis=True)
mem_cache = Cache(cache_name="mem_cache", use_redis=False)
