import functools
import logging
import socket
import sys
from src.config import config_instance


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
    logger = AppLogger(name=name, is_file_logger=not is_development, log_level=logging.CRITICAL)
    return logger.logger
