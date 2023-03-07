import threading
import time
from json import JSONDecodeError
from typing import Any
import redis
import asyncio_redis
import ujson
from redis import ConnectionError
from src.config import config_instance
from src.utils.my_logger import init_logger
from src.utils.utils import camel_to_snake

MEM_CACHE_SIZE = config_instance().CACHE_SETTINGS.MAX_CACHE_SIZE
EXPIRATION_TIME = config_instance().CACHE_SETTINGS.CACHE_DEFAULT_TIMEOUT


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
                self._redis_pool: asyncio_redis.Pool = None
                # self._redis_client = redis.Redis(host=redis_host, port=redis_port, username=username, password=password)
                config_instance().DEBUG and self._logger.info("Using Redis -- Connection Successful")
            except ConnectionError:
                config_instance().DEBUG and self._logger.error(msg="Redis failed to connect....")
                self.turn_off_redis()

    @property
    async def can_use_redis(self):
        return self._use_redis

    async def turn_off_redis(self):
        self._use_redis = False

    async def on_delete(self):
        """
            run when you need to delete all keys
        :return:
        """
        try:
            self._redis_client.flushall(asynchronous=True)
        except ConnectionError:
            config_instance().DEBUG and self._logger.error(msg="Redis failed to connect....")
            # self.turn_off_redis()

    async def _serialize_value(self, value: Any) -> str:
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

    async def _deserialize_value(self, value: any) -> Any:
        """
            Deserialize the given json string to a python object.
        """
        try:
            return ujson.loads(value)
        except JSONDecodeError:
            config_instance().DEBUG and self._logger.error(f"{value}")
            return value
        except TypeError:
            config_instance().DEBUG and self._logger.error(f"{value}")
            return value

    async def _set_mem_cache(self, key: str, value: Any, ttl: int = 0):
        """

        :param key:
        :param value:
        :param ttl:
        :return:
        """

        with self._lock:
            # If the cache is full, remove the oldest entry
            if len(self._cache) >= self.max_size:
                await self._remove_oldest_entry()
            # Add the new entry
            self._cache[key] = {'value': value, 'timestamp': time.time()}
            # self._logger.info(f"Created value : {value}")

    async def set(self, key: str, value: Any, ttl: int = 0):
        """
            Store the value in the cache. If the key already exists, the value is updated.
            If use_redis=True the value is stored in Redis, otherwise it is stored in-memory
        """
        value = await self._serialize_value(value)

        if len(self._cache) > self.max_size:
            await self._remove_oldest_entry()

        if self._use_redis:
            exp_time = ttl if ttl else self.expiration_time
            self._redis_client.set(key, value, ex=exp_time)

        await self._set_mem_cache(key=key, value=value, ttl=ttl)

    async def _get_memcache(self, key: str) -> Any:
        """
            # called by get and set should not be called by user
        :param key:
        :return:
        """
        entry = self._cache.get(key)
        if entry and time.time() - entry['timestamp'] < self.expiration_time:
            value = entry['value']
        else:
            value = None
        return value

    async def get(self, key: str) -> Any:
        """
            Retrieve the value associated with the given key. If use_redis=True
            the value is retrieved from Redis, otherwise it is retrieved from in-memory cache.
        """
        value = await self._get_memcache(key=key)

        if self._use_redis and value is None:
            try:
                value = self._redis_client.get(key)
            except redis.exceptions.TimeoutError:
                config_instance().DEBUG and self._logger.error("Timeout Error Reading from redis")
                value = None
            except redis.exceptions.ConnectionError:
                config_instance().DEBUG and self._logger.error("ConnectionError Reading from redis")
                value = None

        return await self._deserialize_value(value) if value else None

    async def _remove_oldest_entry(self):
        """
        **in-case memory is full remove oldest entries
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
                await self.delete_memcache_key(key=oldest_entry)
                await self.delete_redis_key(key=oldest_entry)

    async def delete_redis_key(self, key):
        self._redis_client.delete([key])

    async def delete_memcache_key(self, key):
        self._cache.pop(key)

    async def delete_key(self, key):
        await self.delete_redis_key(key)
        await self.delete_memcache_key(key)

    async def clear_mem_cache(self):
        """"""
        self._cache = {}

    async def clear_redis_cache(self):
        self._redis_client.flushall(asynchronous=True)

    async def create_redis_pool(self):
        redis_host = config_instance().REDIS_CACHE.CACHE_REDIS_HOST
        redis_port = config_instance().REDIS_CACHE.CACHE_REDIS_PORT
        password = config_instance().REDIS_CACHE.REDIS_PASSWORD
        self._redis_pool = await asyncio_redis.Pool.create(host=redis_host, port=redis_port, password=password,
                                                           poolsize=5)

