# Кастомный скрипт для вывода логов в формате json.
# Необходимо для сохранения docker logs.

# Логика фильтрации реализована через setLevel:
#   - info_handler принимает только INFO и выше, но так как ERROR выше INFO, он перехватывается следующим обработчиком.
#   - error_handler принимает только ERROR и выше.

import logging
from pythonjsonlogger import jsonlogger

def configure_logger() -> logging.Logger:
    logger = logging.getLogger()
    if not logger.handlers:  # Проверяем наличие обработчиков
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            json_ensure_ascii=False,
        )

        # логируем в файл основного Docker процесса
        # INFO -> /proc/1/fd/1
        info_handler = logging.FileHandler("/proc/1/fd/1")
        info_handler.setFormatter(formatter)
        # Данный обработчик логирует только уровень INFO
        info_handler.addFilter(lambda record: record.levelno == logging.INFO)

        # ERROR -> /proc/1/fd/2
        error_handler = logging.FileHandler("/proc/1/fd/2")
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)

        logger.setLevel(logging.INFO)
        logger.addHandler(info_handler)
        logger.addHandler(error_handler)

        # Отключаем логгирование от httpx
        logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger

logger = configure_logger()
