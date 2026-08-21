FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY api ./api

ENV STORE_DIR=/app/data/store
EXPOSE 8080

# Cloud Run injects $PORT — respect it instead of hardcoding 8000
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}
