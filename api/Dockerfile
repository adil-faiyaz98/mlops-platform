FROM python:3.9-slim-buster as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

FROM python:3.9-slim-buster
WORKDIR /app
COPY --from=builder /app .

RUN adduser --disabled-password --gecos "" appuser
USER appuser

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8080"]