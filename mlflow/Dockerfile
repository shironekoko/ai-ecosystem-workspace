# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────
# Dockerfile สำหรับ MLflow Tracking Server
# มี psycopg2-binary สำหรับ PostgreSQL backend store
# และ boto3 สำหรับ MinIO S3 artifact store
# ─────────────────────────────────────────────
FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    mlflow==2.15.1 \
    psycopg2-binary \
    boto3

EXPOSE 5000

CMD ["mlflow", "server"]
