from fastapi import Request, HTTPException, status
from fastapi.routing import APIRoute
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# Define a Pydantic model for API Key validation
class ApiKey(BaseModel):
    api_key: str


# Define a SQLAlchemy model for API Keys
Base = declarative_base()


class ApiKeyModel(Base):
    __tablename__ = 'api_keys'
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String(255), unique=True)


# Connect to the MySQL database
DATABASE_URL = 'mysql+pymysql://root:11111111@localhost:3306/eod-api'
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Define a dict to store API Keys and their rate limit data
api_keys: dict[str, dict[str, int]] = {}


# Define a function to retrieve API Keys from the database and cache them in memory
def cache_api_keys():
    session = Session()
    db_keys = session.query(ApiKeyModel).all()
    print(f" API KEYS : {db_keys} ")
    session.close()
    for db_key in db_keys:
        api_keys[db_key.api_key] = {'requests_count': 0, 'last_request_timestamp': 0}


# Cache the API Keys on startup
cache_api_keys()


# Define a custom APIRoute subclass to validate API Keys
class ApiKeyRoute(APIRoute):
    async def get_route_handler(self):
        handler = await super().get_route_handler()

        async def api_key_handler(request: Request, **kwargs):
            api_key = kwargs.get('api_key')
            if api_key is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='API Key missing')
            if api_key not in api_keys:
                session = Session()
                api_key_model = session.query(ApiKeyModel).filter(ApiKeyModel.api_key == api_key).first()
                if api_key_model is None:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid API Key')
                api_keys[api_key] = {'requests_count': 0, 'last_request_timestamp': 0}
                session.close()
            return await handler(request, **kwargs)

        return api_key_handler
