import functools
from pydantic import BaseSettings, Field


class DatabaseSettings(BaseSettings):
    SQL_DB_URL: str = Field(..., env='SQL_DB_URL')
    TOTAL_CONNECTIONS: int = Field(default=100)

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class ApiServers(BaseSettings):
    MASTER_API_SERVER: str = Field(..., env='MASTER_API_SERVER')
    SLAVE_API_SERVER: str = Field(..., env='SLAVE_API_SERVER')
    X_API_KEY: str = Field(..., env='X_API_KEY')
    X_SECRET_TOKEN: str = Field(..., env='X_SECRET_TOKEN')
    X_RAPID_SECRET: str = Field(..., env='X_RAPID_SECRET')

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class Logging(BaseSettings):
    filename: str = Field(default="eod_stock_api_gateway.logs")

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class Settings(BaseSettings):
    SECRET_KEY: str = Field(..., env="SECRET_TOKEN")
    DATABASE_SETTINGS: DatabaseSettings = DatabaseSettings()
    API_SERVERS: ApiServers = ApiServers()
    DEVELOPMENT_SERVER_NAME: str = Field(default="DESKTOP-T9V7F59")
    LOGGING: Logging = Logging()
    DEBUG: bool = True

    class Config:
        case_sensitive = True
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


@functools.lru_cache
def config_instance():
    return Settings()
