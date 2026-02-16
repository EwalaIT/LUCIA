# ============================
# LangChain Backend (FastAPI)
# ============================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/lang_chain_backend/requirements.txt .
COPY db/ ./db/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY services/lang_chain_backend .

EXPOSE 8000

CMD ["sh", "-c", "python /app/db/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
