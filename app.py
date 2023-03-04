import socket

from src.bootstrap import create_tables
from src.main.main import app
from src.config import config_instance
import uvicorn

# this will create database tables if they do not already exist
create_tables()

if __name__ == '__main__':
    # Start the FastAPI app
    if config_instance().DEVELOPMENT_SERVER_NAME.casefold() == socket.gethostname().casefold():
        uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
    else:
        uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
