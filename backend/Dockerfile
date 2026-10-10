FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/src /app/backend/src
ENV PYTHONPATH=/app/backend/src
CMD ["python", "-m", "marketpulse.worker_main"]
