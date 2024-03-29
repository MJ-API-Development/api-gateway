import functools
from pydantic import BaseSettings, Field, AnyHttpUrl, EmailStr


class DatabaseSettings(BaseSettings):
    SQL_DB_URL: str = Field(..., env='SQL_DB_URL')
    LOCAL_DB_URL: str = Field(..., env='LOCAL_DB_URL')
    TOTAL_CONNECTIONS: int = Field(default=100)

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class ApiServers(BaseSettings):
    MASTER_API_SERVER: str = Field(..., env='MASTER_API_SERVER')
    SLAVE_API_SERVER: str = Field(..., env='SLAVE_API_SERVER')
    SERVERS_LIST: str = Field(..., env='SERVERS_LIST')
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


class RedisSettings(BaseSettings):
    """
    # NOTE: maybe should use Internal pydantic Settings
    # TODO: please finalize Redis Cache Settings """
    CACHE_TYPE: str = Field(..., env="CACHE_TYPE")
    CACHE_REDIS_HOST: str = Field(..., env="CACHE_REDIS_HOST")
    CACHE_REDIS_PORT: int = Field(..., env="CACHE_REDIS_PORT")
    REDIS_PASSWORD: str = Field(..., env="REDIS_PASSWORD")
    REDIS_USERNAME: str = Field(..., env="REDIS_USERNAME")
    CACHE_REDIS_DB: str = Field(..., env="CACHE_REDIS_DB")
    CACHE_REDIS_URL: str = Field(..., env="MICROSOFT_REDIS_URL")
    CACHE_DEFAULT_TIMEOUT: int = Field(default=60 * 60 * 6)

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class CacheSettings(BaseSettings):
    """Google Mem Cache Settings"""
    # NOTE: TO USE Flask_cache with redis set Cache type to redis and setup CACHE_REDIS_URL
    CACHE_TYPE: str = Field(..., env="CACHE_TYPE")
    CACHE_DEFAULT_TIMEOUT: int = Field(default=60 * 60 * 3)
    MEM_CACHE_SERVER_URI: str = Field(default="")
    CACHE_REDIS_URL: str = Field(..., env="CACHE_REDIS_URL")
    MAX_CACHE_SIZE: int = Field(default=1024)
    USE_CLOUDFLARE_CACHE: bool = Field(default=True)

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class EmailSettings(BaseSettings):
    SMTP_SERVER: str = Field(..., env="SMTP_SERVER")
    SMTP_PORT: int = Field(..., env="SMTP_PORT")
    SENDGRID_API_KEY: str = Field(..., env="SENDGRID_API_KEY")
    ADMIN: str = Field(default="noreply@eod-stock-api.site")

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class PayPalSettings(BaseSettings):
    MODE: str = Field(default="live")
    CLIENT_ID: str = Field(..., env="PAYPAL_CLIENT_ID")
    CLIENT_SECRET: str = Field(..., env="PAYPAL_CLIENT_SECRET")
    BEARER_TOKEN: str = Field(..., env="PAYPAL_BEARER_TOKEN")

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class CloudflareSettings(BaseSettings):
    EMAIL: str = Field(..., env="CLOUDFLARE_EMAIL")
    TOKEN: str = Field(..., env="CLOUDFLARE_TOKEN")
    CLOUDFLARE_SECRET_KEY: str = Field(..., env="CLOUDFLARE_SECRET_KEY")

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class AppSettings(BaseSettings):
    app_name: str = "EOD-STOCK-API - API GATEWAY"
    app_description: str = """
        **Stock Marketing & Financial News API**,

        provides end-of-day stock information for multiple exchanges around the world. 
        With this API, you can retrieve data for a specific stock at a given date, or for a range of dates. and also get access
        to companies fundamental data, financial statements, social media trending stocks by sentiment, and also the ability to create a summary of the Financial 
        News Related to a certain stock or company and its sentiment.
    """
    version: str = "1.0.0"
    terms_of_service: AnyHttpUrl = "https://eod-stock-api.site/terms"
    contact_name: str = "EOD-STOCK-API"
    contact_url: AnyHttpUrl = "https://eod-stock-api.site/contact"
    contact_email: EmailStr = "info@eod-stock-api.site"
    license_name: str = "Apache 2.0"
    license_url: AnyHttpUrl = "https://www.apache.org/licenses/LICENSE-2.0.html"
    docs_url: str = None
    openapi_url: str = None
    redoc_url: str = None

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
    PREFETCH_INTERVAL: int = 5
    REDIS_CACHE: RedisSettings = RedisSettings()
    CACHE_SETTINGS: CacheSettings = CacheSettings()
    EMAIL_SETTINGS: EmailSettings = EmailSettings()
    PAYPAL_SETTINGS: PayPalSettings = PayPalSettings()
    CLOUDFLARE_SETTINGS: CloudflareSettings = CloudflareSettings()
    FERNET_KEY: bytes = Field(..., env="FERNET_KEY")
    APP_SETTINGS: AppSettings = AppSettings()

    class Config:
        case_sensitive = True
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


@functools.lru_cache
def config_instance():
    return Settings()
