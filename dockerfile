FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN pip install poetry

COPY pyproject.toml poetry.lock* ./


RUN poetry install --no-interaction --no-ansi

COPY . .
EXPOSE 8005

CMD ["poetry", "run", "task", "start"]