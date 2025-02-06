import os
import logging
from logging.handlers import RotatingFileHandler

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

MAX_LOG_SIZE = 5 * 1024 * 1024
BACKUP_COUNT = 2

log_dir = 'logs'

if not os.path.exists(log_dir):
    os.makedirs(log_dir)


def setup_logger(name: str, log_file: str, console_level: int, file_level: int) -> logging.Logger:
    """
    Создает и настраивает логгер с выводом в файл и консоль.

    :param name: Имя логгера.
    :param log_file: Путь к файлу логов.
    :param console_level: Уровень логов для консоли.
    :param file_level: Уровень логов для файла.
    :return: Настроенный логгер.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)

    file_handler = RotatingFileHandler(log_file, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


parser_logger = setup_logger(
    name="parser_logger",
    log_file="logs/parser.log",
    console_level=logging.INFO,
    file_level=logging.ERROR
)

bot_logger = setup_logger(
    name="bot_logger",
    log_file="logs/bot.log",
    console_level=logging.DEBUG,
    file_level=logging.ERROR
)
