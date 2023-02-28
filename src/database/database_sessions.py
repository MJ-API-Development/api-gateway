from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from src.config import config_instance

DATABASE_URL = config_instance().DATABASE_SETTINGS.SQL_DB_URL
engine = create_engine(DATABASE_URL)

# Define a SQLAlchemy model for API Keys
Base = declarative_base()
sessionType = Session

SESSIONS_PRE_CACHE_SIZE = 150


def get_session() -> Session:
    while True:
        for session in [sessionmaker(bind=engine) for _ in range(SESSIONS_PRE_CACHE_SIZE)]:
            yield session()


sessions = get_session()

