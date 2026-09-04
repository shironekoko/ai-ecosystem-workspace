# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────
# Dockerfile สำหรับ Trainer Worker (GPU Enabled)
# ─────────────────────────────────────────────

# ── Base Image: PyTorch + CUDA + cuDNN ──
# Image นี้มี CUDA 12.1, cuDNN 8, PyTorch 2.3.0 ติดตั้งมาให้แล้ว
# ไม่ต้องติดตั้ง NVIDIA Driver ใน Container → ใช้ Driver ของ Host เครื่องโดยตรง
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

# กำหนด Working Directory ภายใน Container
WORKDIR /app

# ติดตั้ง System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# ── Layer Cache Optimization ──
# Copy requirements.txt ก่อน source code
COPY requirements.txt .

# ติดตั้ง Python dependencies
# --no-cache-dir → ไม่เก็บ Cache ใน Image ให้ขนาดเล็กลง
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy Source Code ──
COPY . .

# คำสั่ง Default: รัน ARQ Worker
CMD ["python", "worker.py"]
