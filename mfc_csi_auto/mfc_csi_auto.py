# Скрипт для создания загрузочного файла CSI МФЦ

# Притягивает файл звонков с явками за вчерашнее число 
# и выполняет его парсинг, после чего загружает полчуенный файл в сервис обзвона.

import requests, os, sys, io
import asyncio
from datetime import datetime, timedelta
from typing import Tuple
from telegram.error import TelegramError

# Кастомные библиотеки
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser_mfc_csi import parcer_csi_mfc
from logger import logger
from telegram_bot import send_telegram_msg

# получение переменных из env
# from dotenv import load_dotenv
# load_dotenv('.env')
# URL = os.getenv("URL")
# TOKEN = os.getenv("TOKEN")
# ENDPOINT = os.getenv("ENDPOINT")
# TG_TOKEN = os.getenv("TG_TOKEN")
# CHANNEL_ID = os.getenv("CHANNEL_ID")

# получение переменных из Docker Compose
URL = os.environ.get("URL")
TOKEN = os.environ.get("TOKEN")
ENDPOINT = os.environ.get("ENDPOINT")
TG_TOKEN = os.environ.get("TG_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# класс ошибок
class ServerRequestError(Exception):
    """Общее исключение для ошибок при отправке данных на сервер."""
    pass

# получение файла с прошедшими звонками
def get_file_calls() -> Tuple[str, io.BytesIO]:
    now = datetime.now() # Время по МСК(локально), время по Гринвичу(сервер)

    start_date = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    # Устанавливаем URL и параметры
    url = f'{URL}?start_date={start_date}&end_date={end_date}'
    headers = {
        'Authorization': f'Basic {TOKEN}', 
        'Content-Type': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            file_data = io.BytesIO(response.content)
            file_data.seek(0)
            filename = f"ВКС-CSI-{end_date}.xlsx"

            logger.info(f"Файл успешно получен как {filename}")
            return filename, file_data
        else:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получениии файла из сервиса:{e}")
        raise ServerRequestError(f"Ошибка при получениии файла из сервиса:{e}")

def send_file_to_server(filename: str, io_file: io.BytesIO) -> None:
    headers = {
        'accept': 'application/json',
        'Authorization': f'Basic {TOKEN}'
    }
    
    try:
        files = [
            ('file', (filename, io_file, 'application/octet-stream'))
        ]
        response = requests.post(
            url=ENDPOINT,
            headers=headers,
            files=files,
        )

        # проверка ответа сервера
        if response.status_code == 200:
            logger.info("Данные успешно отправлены на сервер.")
        else:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке запроса на сервер: {e}")
        raise ServerRequestError(f"Ошибка при отправке запроса на сервер: {e}")

async def main():
    try:
        # получение файла с прошедшими звонками
        filename, file_data = get_file_calls()

        # парсинг полученного файла
        file_after_parsing, row_count = parcer_csi_mfc(file_data)

        # Отправка полученного файла в сервис обзвона
        send_file_to_server(filename, file_after_parsing)

        # отправка сообщения в Telegram
        await send_telegram_msg(row_count, filename, TG_TOKEN, CHANNEL_ID)

    except (ConnectionError, TelegramError, ServerRequestError) as e:
        logger.error(f"Произошла ошибка в процессе выполнения: {e}")

if __name__ == "__main__":
    asyncio.run(main())
