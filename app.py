from src.bootstrap import create_tables
from src.main.main import app
import uvicorn

# this will create database tables if they do not already exist
create_tables()

if __name__ == '__main__':
    # Start the FastAPI app
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
