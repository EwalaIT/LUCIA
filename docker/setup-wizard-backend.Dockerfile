FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Poetry
ENV POETRY_VERSION=1.8.3
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false

# Dependencies
COPY services/setup-wizard-microservice/backend/pyproject.toml \
    services/setup-wizard-microservice/backend/poetry.lock* ./

RUN poetry install --no-interaction --no-ansi --no-root --only main

# App
COPY services/setup-wizard-microservice/backend/setup-wizard-microservice ./

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug", "app:app"]
