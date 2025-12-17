FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry
ENV POETRY_VERSION=1.8.3
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false

# Dependencies
COPY services/setup-wizard-microservice/backend/pyproject.toml \
    services/setup-wizard-microservice/backend/poetry.lock* ./

RUN poetry install --no-interaction --no-ansi --only main

# App
COPY services/setup-wizard-microservice/backend ./

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "setup-wizard-microservice.app:app"]
