import pandas as pd
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

class FileReadError(ParsingError):
    """Исключение для ошибок при чтении файла."""
    pass

def parcer_mfc(file_data: io.BytesIO) -> Tuple[io.BytesIO, str]:
    # Шаг 0: Проверка на пустые данные
    if file_data is None or len(file_data.getvalue()) == 0:
        logger.error("Получен пустой файл. Парсинг отменен.")
        raise EmptyFileError("Получен пустой файл. Парсинг отменен.")

    # Шаг 1: Чтение данных из BytesIO
    try:
        file_data.seek(0)  # Перемещаем курсор в начало данных
        df = pd.read_excel(file_data)  # Загружаем данные из переданного объекта BytesIO
    except Exception as e:
        logger.error(f"Ошибка чтения данных с файла: {e}")
        raise FileReadError(f"Ошибка чтения данных с файла: {e}")

    # Шаг 2: Выделяем только те записи, где в столбце 'Тип записи' значение 'ВКС'
    df_vks = df[df['Тип записи'] == 'ВКС']

    # Шаг 3: Удаляем дубликаты в столбце 'Телефон заяв.', оставляя только одну строку каждого дубля
    df_vks = df_vks.drop_duplicates(subset=['Телефон заяв.'], keep='first')

    # Шаг 4: Удаляем ненужные столбцы
    df_vks = df_vks.drop(columns=['Услуга', 'Отделение', 'Адрес'])

    # Шаг 5: Добавляем новый столбец 'Номер' с заполнением значением '1'
    df_vks['Номер'] = '1'

    # Шаг 6: Преобразуем формат даты в столбце 'Дата Записи'
    df_vks['Дата Записи'] = pd.to_datetime(df_vks['Дата Записи'], format='%d.%m.%y').dt.strftime('%d-%m-%Y')

    # Шаг 7: Добавляем новый столбец 'Адрес' с пустыми значениями
    df_vks['Адрес'] = ''

    # Шаг 8: Переименовываем столбец 'Тип записи' в 'Отделение (МФЦ/ВКС)'
    df_vks = df_vks.rename(columns={'Тип записи': 'Отделение (МФЦ/ВКС)'})

    # Шаг 9: Переупорядочиваем столбцы
    df_vks = df_vks[['Телефон заяв.', 'Адрес', 'Код брон.', 'Отделение (МФЦ/ВКС)', 'Дата Записи', 'Время записи', 'Номер']]

    #  Сохраняем количество строк в файле
    row_count = str(df_vks.shape[0])

    # Шаг 10: Сохраняем результат в объект BytesIO
    output_file = io.BytesIO()
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df_vks.to_excel(writer, index=False)
    output_file.seek(0)

    logger.info(f"Парсинг завершен! Количество заявок в файле: {row_count}")

    # Возвращаем объект BytesIO и кол-во заявок
    return output_file, row_count