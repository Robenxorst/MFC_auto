import pandas as pd
from datetime import datetime, timedelta
import io, sys, os
from typing import Tuple

# кастомная библиотека
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logger import logger

class ParsingError(Exception):
    """Общее исключение для ошибок при парсинге данных."""
    pass

class EmptyFileError(ParsingError):
    """Исключение для ошибок пустого файла."""
    pass


def parcer_csi_mfc(file_data: io.BytesIO) -> Tuple[io.BytesIO, str]:

    if file_data is None or len(file_data.getvalue()) == 0:
        logger.error("Получены пустые данные. Парсинг не выполнен.")
        raise EmptyFileError("Получены пустые данные. Парсинг не выполнен.")

    # Загружаем данные из файла
    file_data.seek(0)
    df = pd.read_excel(file_data)

    # Получаем вчерашнюю дату
    now = datetime.now() # Время по МСК(локально), время по Гринвичу(сервер)
    last_day = (now - timedelta(days=1)).strftime("%d-%m-%Y")

    # Выделяем только те записи, где в столбце 'Дата записи' проставлено вчерашняя дата
    df_csi = df[df['Дата записи'] == last_day]

    # Удаляем не подтвержденных
    df_csi = df_csi.drop(df_csi[df_csi['Статус звонка'].isin(['Не+подтвержден', 'Запись+перенесена+или+отменена', 'Не+звонить', 'Не+записывался'])].index)

    # Удаляем ненужные столбцы
    df_csi = df_csi.drop(columns=['Счётчик успешных дозвонов', 'Счётчик недозвонов', 'Дата загрузки', 'Дата удаления', 'Статус звонка', 'Номер проекта'])

    # Изменяем названия столбцов
    df_csi.rename(columns={'Телефон': 'Телефон заяв.', 'Код бронирования': 'Код брон.', 'Отделение (МФЦ / ВКС':'Отделение (МФЦ/ВКС)'}, inplace=True)

    # Добавляем номер проекта
    df_csi['Номер'] = '2'

    # Удаляем дубликаты в столбце 'Телефон заяв.', оставляя только последнюю строку дубля
    df_csi = df_csi.drop_duplicates(subset=['Телефон заяв.'], keep='last')

    # Получаем количество заявок в файле
    row_count = str(df_csi.shape[0])

    # сохраняем результат парсинга
    output_file = io.BytesIO()
    df_csi.to_excel(output_file, index=False)
    output_file.seek(0)
    
    logger.info(f"Парсинг завершен! Количество заявок в файле: {row_count}")
    return output_file, row_count