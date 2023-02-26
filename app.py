from src.main.main import app
import uvicorn

if __name__ == '__main__':
    # Start the FastAPI app
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
