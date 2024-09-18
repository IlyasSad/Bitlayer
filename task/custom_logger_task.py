import sys
from loguru import logger

def logging_setup():
    """Настройка логгера с цветным выводом и записью в файл."""
    format_info = "<green>{time:HH:mm:ss.SS}</green> | <blue>{level}</blue> | <level>{message}</level>"
    logger.remove()  # Удаляем стандартный логгер

    # Логирование в консоль с цветным оформлением
    logger.add(sys.stdout, colorize=True, format=format_info, level="INFO")

    # Логирование в файл с ротацией (по 50 MB на файл) и компрессией
    logger.add("task.log", rotation="50 MB", compression="zip", format=format_info, level="TRACE")

# Вызов настройки логгирования
logging_setup()
