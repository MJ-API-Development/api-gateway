import socket
from src.main.main import app
from src.config import config_instance
import uvicorn

# this will create database tables if they do not already exist


if __name__ == '__main__':
    # Start the FastAPI app
    if config_instance().DEVELOPMENT_SERVER_NAME.casefold() == socket.gethostname().casefold():
        uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True, workers=1)
    else:
        uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=False, workers=1)
