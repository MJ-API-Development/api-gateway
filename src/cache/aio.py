import ast
import functools

import aiocache
import threading
from typing import Optional
from aiocache.backends.redis import RedisBackend
from aiocache.backends.memory import SimpleMemoryBackend as MemoryBackend

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

    def __init__(
            self,
            cache_name: str = "mem",
            max_size: int = MEM_CACHE_SIZE,
            expiration_time: int = EXPIRATION_TIME,
            use_redis: bool = False,
            redis_host: Optional[str] = None,
            redis_port: Optional[int] = None,
            redis_password: Optional[str] = None,
    ):
        """
        Initializes the cache and creates a cacheio client with either a Redis backend or a Memory backend.

        If Redis fails, the cache will fall back to using an in-memory cache.

        :param cache_name: The name of the cache. This will be used as a prefix for Redis keys.
        :param max_size: The maximum size of the in-memory cache.
        :param expiration_time: The expiration time of each cache entry, in seconds.
        :param use_redis: Indicates whether to use a Redis cache.
        :param redis_host: The hostname of the Redis server.
        :param redis_port: The port number of the Redis server.
        :param redis_password: The password to use when connecting to the Redis server.
        """
        self.max_size = max_size
        self.expiration_time = expiration_time
        self._cache_name = cache_name
        self._use_redis = use_redis
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))
        if self._use_redis:
            redis_host = config_instance().REDIS_CACHE.CACHE_REDIS_HOST
            redis_port = config_instance().REDIS_CACHE.CACHE_REDIS_PORT
            redis_password = config_instance().REDIS_CACHE.REDIS_PASSWORD
            redis_db = config_instance().REDIS_CACHE.CACHE_REDIS_DB
            try:
                self._cache = RedisBackend(
                    endpoint=redis_host,
                    port=redis_port,
                    password=redis_password)
                config_instance().DEBUG and self._logger.info("Using Redis -- Connection Successful")
            except Exception:
                config_instance().DEBUG and self._logger.error(msg="Redis failed to connect....")
                self._use_redis = False
        if not self._use_redis:
            self._cache = MemoryBackend()
        self._lock = threading.Lock()

    async def get(self, key: str, default=None):
        with self._lock:
            value = await self._cache.get(key, default=default)
            if not isinstance(value, dict):
                if value:
                    value = ast.literal_eval(value)
        return value

    async def set(self, key: str, value, expire: Optional[int] = None):
        with self._lock:
            await self._cache.set(key, value, ttl=expire or self.expiration_time)

    async def delete(self, key: str):
        with self._lock:
            await self._cache.delete(key)

    async def clear(self):
        with self._lock:
            await self._cache.clear()
