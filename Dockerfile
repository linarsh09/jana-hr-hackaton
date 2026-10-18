FROM python:3.12-slim

WORKDIR /app

# Build dependencies for psycopg2 (including pg_config).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Создаём виртуальное окружение
RUN python -m venv $VIRTUAL_ENV

# Устанавливаем зависимости в venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY . .

EXPOSE 5000

# Prepare the database after Compose has waited for PostgreSQL to become healthy.
CMD ["sh", "-c", "flask --app app db upgrade && python seeders.py && exec flask --app app run --host=0.0.0.0 --port=5000"]
