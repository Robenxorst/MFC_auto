# Для получения файла с почты используется протокол IMAP
# В качестве сервера IMAP используется сервер optimal-city
# Скрипт запускается в 9:00 и 14:00;

#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import asyncio
import imaplib
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple
import os, sys, io, email
from email.header import decode_header

# Поиск модулей в директории выше
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Кастомные библиотеки
from telegram_bot import send_telegram_msg
from parser_mfc import parcer_mfc
from logger import logger

# Получение переменных окружения из .env
# from dotenv import load_dotenv
# load_dotenv('.env')
# EMAIL = os.getenv("EMAIL")
# PASSWORD = os.getenv("PASSWORD")
# IMAP_SERVER = os.getenv("IMAP_SERVER")
# IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
# ENDPOINT = os.getenv("ENDPOINT")
# TOKEN = os.getenv("TOKEN")
# TG_TOKEN = os.getenv("TG_TOKEN")
# CHANNEL_ID = os.getenv("CHANNEL_ID")

# для получения переменных окружения из Docker Compose
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
IMAP_SERVER = os.environ.get("IMAP_SERVER")
IMAP_PORT = int(os.environ.get("IMAP_PORT"))
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get("TOKEN")
TG_TOKEN = os.environ.get("TG_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# Классы исключений
class MailFetchError(Exception):
    """Исключение для ошибок при получении данных с почтового сервера"""
    pass

class MailSearchError(Exception):
    """Исключение для ошибок при поиске писем"""
    pass

class ServerRequestError(Exception):
    """Общее исключение для ошибок при отправке данных на сервер."""
    pass

# функция для декодирования названия файла
def decode_filename(encoded_filename):
    decoded_parts = decode_header(encoded_filename)
    decoded_filename = ''.join(
        part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
        for part, encoding in decoded_parts
    )
    return decoded_filename

# Функция для подключения к почтовому серверу IMAP
def connect_to_mail() -> Optional[imaplib.IMAP4_SSL]:

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL, PASSWORD)
        logger.info("Успешное подключение к серверу почты.")
        return mail
    except imaplib.IMAP4.error as e:
        logger.error(f"Не удалось подключиться к почтовому серверу: {e}")
        raise ConnectionError("Не удалось подключиться к почтовому серверу.")


# Функция получения данных с почты
def get_attachment_data(mail: imaplib.IMAP4_SSL) -> Tuple[str, io.BytesIO]:

    mail.select("inbox")

    # Получение списка идентификаторов писем, отправленных сегодня
    now = datetime.now()
    since_date = (now - timedelta(hours=5)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'SINCE {since_date}')
    if status != "OK" or not messages:
        raise MailSearchError(f"Ошибка в поиске писем: статус {status} или нет сообщений за сегодня.")

    messages = messages[0].split()
    msg_id = messages[-1]  # всегда берем самое последнее сообщение

    status, msg_data = mail.fetch(msg_id, "(RFC822)")
    if status != "OK":
        raise MailFetchError(f"Ошибка в получении данных по id сообщения {msg_id}. Статус: {status}")

    response_part = msg_data[0] # response_part - type bytes
    msg = email.message_from_bytes(response_part[-1])  # создаем объект сообщения
    for part in msg.walk():

        if part.get_content_maintype() == "application" and part.get_filename():
            encoded_filename = part.get_filename() # закодированное название файла
            filename = decode_filename(encoded_filename)  # Декодируем имя файла 
                
            if filename.lower().endswith((".xls", ".xlsx")):
                file_data = part.get_payload(decode=True)
                logger.info(f"Файл {filename} получен.")
                return filename, io.BytesIO(file_data)

    raise MailFetchError("Excel документ не найден в письме")



def send_file_to_server(io_file: io.BytesIO, filename: str) -> None:
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
            logger.info("Данные успешно загружены на сервер.")
        else:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка в отправке данных на сервер: {e}")
        raise ServerRequestError(f"Ошибка в отправке данных на сервер: {e}")

async def main():
    try:
        # Подключаемся к почте и получаем данные
        mail = connect_to_mail()
        filename, file_data = get_attachment_data(mail)
        mail.logout()

        # Парсим данные с файла
        file_until_parcer, row_count = parcer_mfc(file_data)

        # Отправляем обработанный файл на сервер
        send_file_to_server(file_until_parcer, filename)

        # Отправляем сообщение в Telegram
        await send_telegram_msg(row_count, filename, TG_TOKEN, CHANNEL_ID)
    
    except (ConnectionError, MailSearchError, MailFetchError, ServerRequestError) as e:
        logger.error(f"Во время выполнения произошла ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
