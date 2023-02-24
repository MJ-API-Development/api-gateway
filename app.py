import asyncio
import threading
import uvicorn

from src.main.main import app, prefetch_endpoints

#
# def run_async_in_thread():
#     asyncio.run(prefetch_endpoints())
#
#
# # Spawn a new thread to prefetch the endpoints
# thread = threading.Thread(target=run_async_in_thread)
# thread.start()

if __name__ == '__main__':
    # Start the FastAPI app
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
