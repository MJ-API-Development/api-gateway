import functools
import logging
import os
import socket
import sys
from src.config import config_instance
from cryptography.fernet import Fernet


class MyFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key: bytes = config_instance().FERNET_KEY

    def format(self, record):
        # Customize the format of the log message here
        return f"[{record.asctime}] {record.name} - {record.levelname}: {self.encrypt_log(record.message)}"

    @staticmethod
    def create_256_key() -> bytes:
        # Convert the secret key to bytes
        return Fernet.generate_key()

    def encrypt_log(self, log: str):
        # encrypt the log message
        return Fernet(self.key).encrypt(log.encode('utf-8'))

    def decrypt_log(self, log: bytes) -> str:
        """decrypting logs"""
        return Fernet(key=self.key).decrypt(token=log).decode('utf-8')

    def decrypt_formatted_log(self, formatted_log: str) -> str:
        # Extract the encrypted message from the formatted log string
        parts = formatted_log.split(":")
        encrypted_message = parts[-1].strip()

        # Decrypt the message and replace the encrypted message in the formatted string with the decrypted message
        decrypted_message = self.decrypt_log(encrypted_message.encode("utf-8")).strip()
        parts[-1] = decrypted_message
        return ":".join(parts)


class AppLogger:
    def __init__(self, name: str, is_file_logger: bool = False, log_level: int = logging.INFO):
        # TODO create the logs folder in the root directory of the application
        logging_file = f'logs/{config_instance().LOGGING.filename}'
        logger_name = name if name else config_instance().APP_NAME
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(level=log_level)

        handler = logging.FileHandler(logging_file) if is_file_logger else logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)


@functools.lru_cache
def init_logger(name: str = "eod-stock-api"):
    """
        should include a future version which uses azure monitor to create log messages
    :param name:
    :return:
    """
    is_development = socket.gethostname() == config_instance().DEVELOPMENT_SERVER_NAME
    logger = AppLogger(name=name, is_file_logger=not is_development, log_level=logging.INFO)
    return logger.logger


