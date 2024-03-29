import asyncio
import functools
import pickle
import threading
import time
from json import JSONDecodeError
from typing import Any, Callable

import asyncio_redis
import redis
from redis import ConnectionError, AuthenticationError

from src.config import config_instance
from src.utils.my_logger import init_logger
from src.utils.utils import camel_to_snake

MEM_CACHE_SIZE = config_instance().CACHE_SETTINGS.MAX_CACHE_SIZE
EXPIRATION_TIME = config_instance().CACHE_SETTINGS.CACHE_DEFAULT_TIMEOUT


class RedisErrorManager:
    """
        Custom Circuit Breaker Error manager for redis cache management
    """
    def __init__(self, use_redis: bool = True):
        self.use_redis: bool = use_redis
        self._permanent_off = use_redis

        self.cache_errors: int = 0

        self.error_threshold: int = 10
        self.min_error_threshold: int = 5
        self.initial_off_time: int = 60
        self.max_off_time: int = 3600
        self.time_since_last_error: int = 0

    async def turn_off_redis(self, off_time: int):
        self.use_redis = False
        self.time_since_last_error = 0
        # additional code to shut down Redis or perform other tasks
        if off_time == 0:
            self._permanent_off = False
            return

        await asyncio.sleep(off_time)

    async def turn_on_redis(self):
        self.use_redis = True
        # additional code to initialize Redis or perform other tasks

    async def check_error_threshold(self):
        if self.cache_errors >= self.error_threshold and self.time_since_last_error <= self.max_off_time:
            off_time = self.initial_off_time * 2 ** (self.cache_errors - self.min_error_threshold)
            off_time = min(off_time, self.max_off_time)
            await self.turn_off_redis(off_time)
        elif self.cache_errors < self.min_error_threshold and not self.use_redis:
            await self.turn_on_redis()
        else:
            self.time_since_last_error += 1

    async def increment_cache_errors(self):
        self.cache_errors += 1

    async def can_use_redis(self):
        return self.use_redis and self._permanent_off


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
        self.redis_errors = RedisErrorManager(use_redis=use_redis)
        self._cache = {}
        self._cache_lock = threading.Lock()

        self._logger = init_logger(camel_to_snake(self.__class__.__name__))

        if self.redis_errors.use_redis:
            redis_host = config_instance().REDIS_CACHE.CACHE_REDIS_HOST
            redis_port = config_instance().REDIS_CACHE.CACHE_REDIS_PORT
            password = config_instance().REDIS_CACHE.REDIS_PASSWORD
            # Azure Redis not using username, may use it in the future in case we are changing to another redis client
            # or using multiple redis clients at the same time
            # noinspection PyUnusedLocal
            username = config_instance().REDIS_CACHE.REDIS_USERNAME
            try:
                self._redis_client = redis.Redis(host=redis_host, port=redis_port, password=password)
                self._redis_pool: asyncio_redis.Pool = None
                # self._redis_client = redis.Redis(host=redis_host, port=redis_port, username=username, password=password)
                config_instance().DEBUG and self._logger.info("Cache -- Redis connected")
            except (ConnectionError, AuthenticationError):
                config_instance().DEBUG and self._logger.error(msg="Redis failed to connect....")
                self.redis_errors.turn_off_redis(off_time=0)

    @property
    async def can_use_redis(self) -> bool:
        return await self.redis_errors.can_use_redis()

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
        except TypeError:
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
        with self._cache_lock:
            # If the cache is full, remove the oldest entry
            if len(self._cache) >= self.max_size:
                await self._remove_oldest_entry()

            # creates a mem_cache item and set the timestamp and time to live based on given value or default
            self._cache[key] = {'value': value, 'timestamp': time.monotonic(), 'ttl': ttl}

    async def set(self, key: str, value: Any, ttl: int = 0):
        """
             Store the value in the cache. If the key already exists, the value is updated.

            :param key: str - a unique identifier for the cached value
            :param value: Any - the value to be cached
            :param ttl: int, optional - the time-to-live of the cached value in seconds;
                       if not provided, the default expiration time of the cache is used.

            If use_redis=True the value is stored in Redis, otherwise it is stored in-memory.

            :return: None
        """
        value = await self._serialize_value(value, value)
        # setting expiration time
        exp_time = ttl if ttl else self.expiration_time

        if len(self._cache) > self.max_size:
            await self._remove_oldest_entry()

        try:
            if await self.redis_errors.can_use_redis():
                self._redis_client.set(key, value, ex=exp_time)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            # TODO -- keep a count of redis errors if they pass a thresh-hold then switch-off redis
            await self.redis_errors.increment_cache_errors()
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
            await self.redis_errors.increment_cache_errors()
            value = None

        # will only try and return a value in redis if memcache value does not exist
        if await self.redis_errors.can_use_redis() and (value is None):
            try:
                # Wait for the result of the redis lookup with a timeout
                redis_get = functools.partial(_async_redis_get, get=self._redis_client.get)
                value = await asyncio.wait_for(redis_get(_key=key), timeout=timeout)
            except (redis.exceptions.TimeoutError, asyncio.TimeoutError):
                # Timed out waiting for the redis lookup
                config_instance().DEBUG and self._logger.error("Timeout Error Reading from redis")
                await self.redis_errors.increment_cache_errors()
                value = None
            except redis.exceptions.ConnectionError:
                config_instance().DEBUG and self._logger.error("ConnectionError Reading from redis")
                await self.redis_errors.increment_cache_errors()
                value = None

        return await self._deserialize_value(value, value) if value else None

    async def _remove_oldest_entry(self):
        """
        **in-case memory is full remove oldest entries
             Remove the oldest entry in the in-memory cache.
        :return:
        """
        with self._cache_lock:
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
        with self._cache_lock:
            self._redis_client.delete(key)

    async def delete_memcache_key(self, key):
        """ Note: do not use pop"""
        with self._cache_lock:
            del self._cache[key]

    async def delete_key(self, key):
        await self.delete_redis_key(key)
        await self.delete_memcache_key(key)

    async def clear_mem_cache(self):
        """will completely empty mem cache"""
        with self._cache_lock:
            self._cache = {}

    async def clear_redis_cache(self):
        with self._cache_lock:
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
        for key in list(self._cache.keys()):
            # Time has progressed past the allocated time for this resource
            # NOTE for those values where timeout is not previously declared the Assumption is 1 Hour
            value = self._cache[key]
            if value.get('timestamp', 0) + value.get('ttl', 60 * 60) < now:
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
