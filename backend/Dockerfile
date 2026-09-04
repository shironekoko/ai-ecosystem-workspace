# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────
# Dockerfile สำหรับ FastAPI Backend
# ─────────────────────────────────────────────

# ── Stage: Base Python Image ──
FROM python:3.12-slim

# ติดตั้ง System Dependencies ที่จำเป็น (build-essential, libpq-dev, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# กำหนด Working Directory ภายใน Container
WORKDIR /app

# ติดตั้ง uv (Package Manager)
RUN pip install --no-cache-dir uv

# ── Layer Cache Optimization ──
# Copy dependency files ก่อน source code
# เพื่อให้ Docker Cache Layer นี้ไว้ (ถ้า source code เปลี่ยนแต่ dependency ไม่เปลี่ยน
# → ไม่ต้อง uv sync ซ้ำ ประหยัดเวลา Build มาก)
COPY pyproject.toml uv.lock* ./

# ติดตั้ง dependencies ทั้งหมดจาก pyproject.toml
RUN uv sync --no-dev

# ── Copy Source Code ──
# Copy หลังสุดเพื่อใช้ประโยชน์จาก Docker Layer Cache
COPY . .

# เปิด Port 8000 (บอก Docker ว่า Container ใช้ Port นี้)
EXPOSE 8000

# คำสั่ง Default เมื่อ Container รัน
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
