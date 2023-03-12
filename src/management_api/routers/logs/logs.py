import os

from fastapi import APIRouter
from starlette.responses import JSONResponse

from src.config import config_instance
from src.management_api.admin.authentication import authenticate_app, get_headers
from src.utils.my_logger import EncryptedFormatter

log_router = APIRouter()


@log_router.get("/_admin/logs/{num_logs}")
@authenticate_app
async def get_logs(num_logs: int = 50):
    """will retrieve encrypted logs and display on the admin app"""
    log_filename = config_instance().LOGGING.filename
    log_file_path = os.path.join("logs", log_filename)

    # Create a log formatter with the encryption key from the config
    encrypted_logs = EncryptedFormatter()

    # Open the log file and read the last `num_logs` lines (or all lines if `num_logs` is not specified)
    with open(log_file_path, "r") as f:
        if num_logs:
            lines = f.readlines()[-num_logs:]
        else:
            lines = f.readlines()

    # Decrypt each line and return the decrypted log messages
    decrypted_logs = []
    for line in lines:
        decrypted_log = encrypted_logs.decrypt_formatted_log(line)
        decrypted_logs.append(decrypted_log)

    payload = dict(status=True, logs=decrypted_logs, message="logs found")
    _headers = await get_headers(user_data=payload)
    return JSONResponse(content=payload, status_code=200, headers=_headers)

