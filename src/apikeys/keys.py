from fastapi import Request, HTTPException, status
from fastapi.routing import APIRoute
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.config import config_instance

# Define a dict to store API Keys and their rate limit data
api_keys: dict[str, dict[str, int]] = {}
UUID_LEN: int = 16
STR_LEN: int = 255
NAME_LEN: int = 128
EMAIL_LEN: int = 255
CELL_LEN: int = 13
API_KEY_LEN: int = 64
DATABASE_URL = config_instance().DATABASE_SETTINGS.SQL_DB_URL


# Define a Pydantic model for API Key validation
class ApiKey(BaseModel):
    uuid: str
    api_key: str
    subscription_id: str
    duration: int
    limit: int


# Define a SQLAlchemy model for API Keys
Base = declarative_base()


class ApiKeyModel(Base):
    __tablename__ = 'eod_api_keys'
    uuid: str = Column(String(UUID_LEN), index=True)
    api_key: str = Column(String(API_KEY_LEN), primary_key=True, index=True)
    subscription_id: str = Column(String(UUID_LEN))
    duration: int = Column(Integer)
    limit: int = Column(Integer)
    is_active: bool = Column(Boolean, default=True)

    def to_dict(self) -> dict[str, str]:
        return {
            "uuid": self.uuid,
            "api_key": self.api_key,
            "subscription_id": self.subscription_id,
            "duration": self.duration,
            "limit": self.limit}


def get_session():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


# Define a function to retrieve API Keys from the database and cache them in memory
def cache_api_keys():
    session = get_session()()
    db_keys = session.query(ApiKeyModel).all()
    print(f" API KEYS : {db_keys} ")
    session.close()
    for db_key in db_keys:
        # setting counters for api_keys
        api_keys[db_key.api_key] = {'requests_count': 0,
                                    'last_request_timestamp': 0,
                                    'duration': db_key.duration,
                                    'limit': db_key.limit}


# Define a custom APIRoute subclass to validate API Keys
class ApiKeyRoute(APIRoute):
    async def get_route_handler(self):
        handler = await super().get_route_handler()

        async def api_key_handler(request: Request, **kwargs):
            api_key = kwargs.get('api_key')
            if api_key is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='API Key missing')
            if api_key not in api_keys:
                session = get_session()()
                api_key_model = session.query(ApiKeyModel).filter(ApiKeyModel.api_key == api_key).first()
                if api_key_model is None:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid API Key')
                api_keys[api_key] = {'requests_count': 0,
                                     'last_request_timestamp': 0,
                                     'duration': api_key_model.duration,
                                     'limit': api_key_model.limit}

                session.close()
            return await handler(request, **kwargs)

        return api_key_handler
