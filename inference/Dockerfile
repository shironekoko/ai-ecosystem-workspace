FROM ai-ecosystem-workspace-trainer-worker:latest

WORKDIR /app

RUN pip install --no-cache-dir "protobuf<5.0.0" opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

COPY . .

CMD ["python", "worker.py"]