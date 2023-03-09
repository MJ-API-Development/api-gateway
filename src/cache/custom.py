import asyncio
import functools
import threading
import time
from json import JSONDecodeError
from typing import Any, Callable
import redis
import asyncio_redis
import ujson
from redis import ConnectionError, RedisError, AuthenticationError
from src.config import config_instance
from src.utils.my_logger import init_logger
from src.utils.utils import camel_to_snake
import pickle

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
                config_instance().DEBUG and self._logger.info("Cache -- Redis connected")
            except (ConnectionError, AuthenticationError):
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

    async def _serialize_value(self, value: Any, default=None) -> str:
        """
            Serialize the given value to a json string.
        """
        try:
            return pickle.dumps(value)
        except (JSONDecodeError, pickle.PicklingError):
            config_instance().DEBUG and self._logger.error(f"Serializer Error")
            return default
        except TypeError as e:
            config_instance().DEBUG and self._logger.error(f"Serializer Error")
            return default

    async def _deserialize_value(self, value: any, default=None) -> Any:
        """
            Deserialize the given json string to a python object.
        """
        try:
            return pickle.loads(value)
        except (JSONDecodeError, pickle.UnpicklingError):
            config_instance().DEBUG and self._logger.error(f"Error Deserializing Data")
            return default
        except TypeError:
            config_instance().DEBUG and self._logger.error(f"Error Deserializing Data")
            return default

    async def _set_mem_cache(self, key: str, value: Any, ttl: int = 0):
        """
            **_set_mem_cache**
                private method never call this code directly
        :param key:
        :param value:
        :param ttl:
        :return:
        """
        with self._lock:
            # If the cache is full, remove the oldest entry
            if len(self._cache) >= self.max_size:
                await self._remove_oldest_entry()

            # creates a mem_cache item and set the timestamp and time to live based on given value or default
            self._cache[key] = {'value': value, 'timestamp': time.monotonic(), 'ttl': ttl}

    async def set(self, key: str, value: Any, ttl: int = 0):
        """
            Store the value in the cache. If the key already exists, the value is updated.
            If use_redis=True the value is stored in Redis, otherwise it is stored in-memory
        """
        value = await self._serialize_value(value, value)
        # setting expiration time
        exp_time = ttl if ttl else self.expiration_time

        if len(self._cache) > self.max_size:
            await self._remove_oldest_entry()

        try:
            if self._use_redis:
                self._redis_client.set(key, value, ex=exp_time)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            # TODO -- keep a count of redis errors if they pass a thresh-hold then switch-off redis
            pass
        try:
            await self._set_mem_cache(key=key, value=value, ttl=exp_time)
        except KeyError:
            pass

    async def _get_memcache(self, key: str) -> Any:
        """
            # called by get and set should not be called by user
        :param key:
        :return:
        """
        entry = self._cache.get(key, {})
        if entry and time.monotonic() - entry['timestamp'] < self.expiration_time:
            value = entry['value']
        else:
            # await self.delete_key(key)
            value = None
        return value

    # 1 second timeout default
    async def get(self, key: str, timeout=1) -> Any:
        """
        *GET*
            NOTE This method will time-out in 1 second if no value is returned from any cache
                Retrieve the value associated with the given key within the allocated time.
                If use_redis=True the value is retrieved from Redis, only if that key is not also on local memory.

        :param timeout: timeout in seconds, if time expires the method will return None
        :param key = a key used to find the value to search for.
        """

        async def _async_redis_get(get: Callable, _key: str):
            """async stub to fetch data from redis"""
            return get(_key)
        try:
            # Wait for the result of the memcache lookup with a timeout
            value = await asyncio.wait_for(self._get_memcache(key=key), timeout=timeout)
        except (asyncio.TimeoutError, KeyError):
            # Timed out waiting for the memcache lookup, or KeyError - as a result of cache eviction
            value = None

        # will only try and return a value in redis if memcache value does not exist
        if self._use_redis and (value is None):
            try:
                # Wait for the result of the redis lookup with a timeout
                redis_get = functools.partial(_async_redis_get, get=self._redis_client.get)
                value = await asyncio.wait_for(redis_get(_key=key), timeout=timeout)
            except (redis.exceptions.TimeoutError, asyncio.TimeoutError):
                # Timed out waiting for the redis lookup
                config_instance().DEBUG and self._logger.error("Timeout Error Reading from redis")
                value = None
            except redis.exceptions.ConnectionError:
                config_instance().DEBUG and self._logger.error("ConnectionError Reading from redis")
                value = None

        return await self._deserialize_value(value, value) if value else None

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

            # Remove the oldest entry from all caches
            if oldest_entry is not None:
                await self.delete_memcache_key(key=oldest_entry)
                await self.delete_redis_key(key=oldest_entry)

    async def delete_redis_key(self, key):
        """removes a single redis key"""
        with self._lock:
            self._redis_client.delete([key])

    async def delete_memcache_key(self, key):
        with self._lock:
            self._cache.pop(key)

    async def delete_key(self, key):
        with self._lock:
            await self.delete_redis_key(key)
            await self.delete_memcache_key(key)

    async def clear_mem_cache(self):
        """will completely empty mem cache"""
        with self._lock:
            self._cache = {}

    async def clear_redis_cache(self):
        with self._lock:
            self._redis_client.flushall(asynchronous=True)

    async def memcache_ttl_cleaner(self) -> int:
        """
            **memcache_ttl_cleaner**
                will run every ten minutes to clean up every expired mem cache item
                expiration is dependent on ttl
        :return:
        """
        now = time.monotonic()
        # Cache Items are no more than 1024 therefore this is justifiable
        t_c = 0
        for key, value in self._cache.items():
            # Time has progressed past the allocated time for this resource
            # NOTE for those values where timeout is not previously declared the Assumption is 1 Hour
            if value.get('timestamp', 0) + value.get('ttl', 60*60) < now:
                await self.delete_memcache_key(key=key)
                t_c += 1
        return t_c

    async def create_redis_pool(self):
        """
            Eventually Use redis pools to store data to redis
        :return:
        """
        redis_host = config_instance().REDIS_CACHE.CACHE_REDIS_HOST
        redis_port = config_instance().REDIS_CACHE.CACHE_REDIS_PORT
        password = config_instance().REDIS_CACHE.REDIS_PASSWORD
        self._redis_pool = await asyncio_redis.Pool.create(host=redis_host,
                                                           port=redis_port,
                                                           password=password,
                                                           poolsize=5)

