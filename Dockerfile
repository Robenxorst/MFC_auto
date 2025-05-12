FROM python:3.9-slim

WORKDIR /mfc_auto_parcer

COPY . /mfc_auto_parcer

RUN pip install --upgrade pip && pip install -r requirements.txt

# Запускаем процесс в фоновом режиме, чтобы контейнер был "жив"
CMD tail -f /dev/null

# Заметка: фоновый процесс является для Docker основным. 
# Логирование других процессов (например, запуск скриптов) происходить не будет.
# Для логирования сторонних процессов необходимо перенаправлять их вывод на устройства:
# /proc/1/fd/1(stdout) и /proc/1/fd/2(stderr)