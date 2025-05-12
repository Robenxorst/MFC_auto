# Кастомная библиотека для отправки сообщений в TG бота
# Работает с помощью ассинхронных методов (asyncio)

import sys, os
from telegram import Bot
from telegram.error import TelegramError

# кастомная библиотека
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logger import logger


# Асинхронная функция отправки уведомления в Telegram
async def send_telegram_msg(row_count: str, filename: str, token: str, channel_id: str) -> bool:
    bot = Bot(token=token)
    message = (
        f"**Сформирован и отправлен файл:** {filename}\n"
        f"**Количество записей в файле:** {row_count}\n"
    )

    try:
        await bot.send_message(
            chat_id=channel_id,
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"Уведомление успешно отправлено в Telegram")
        return True
    except TelegramError as e:
        logger.error(f"Ошибка при отправке уведомления для Telegram: {e}")
        return False
