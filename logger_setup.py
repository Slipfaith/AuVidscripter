"""Logging configuration for the application."""

import logging
import warnings
import sys
from pathlib import Path
from datetime import datetime


def setup_logging():
    """Configure logging and warning filters."""
    # Подавляем предупреждения
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
    warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

    # Создаем директорию для логов если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Имя файла лога с датой
    log_filename = log_dir / f"transcriber_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Настройка форматирования
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Настройка обработчиков
    handlers = [
        # Файловый обработчик
        logging.FileHandler(log_filename, encoding='utf-8'),
        # Консольный обработчик (только для ошибок)
        logging.StreamHandler(sys.stderr)
    ]

    # Настройка корневого логгера
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

    # Настройка уровней для конкретных логгеров
    logging.getLogger("whisper").setLevel(logging.ERROR)
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)

    # Консольный обработчик показывает только ошибки
    console_handler = handlers[1]
    console_handler.setLevel(logging.ERROR)

    # Логируем начало работы
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Приложение запущено")
    logger.info(f"Лог файл: {log_filename}")
    logger.info("=" * 50)