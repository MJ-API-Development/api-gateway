from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from src.config import config_instance

DATABASE_URL = config_instance().DATABASE_SETTINGS.SQL_DB_URL
engine = create_engine(DATABASE_URL)

# Define a SQLAlchemy model for API Keys
Base = declarative_base()
sessionType = Session


def get_session():
    while True:
        for session in [sessionmaker(bind=engine) for _ in range(50)]:
            yield session()


sessions = get_session()

