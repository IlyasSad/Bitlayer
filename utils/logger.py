from loguru import logger

def setup_logger():
    logger.add("logs/info.log", format="{time} {level} {message}", level="INFO", rotation="10 MB")
    logger.add("logs/error.log", format="{time} {level} {message}", level="ERROR", rotation="10 MB")