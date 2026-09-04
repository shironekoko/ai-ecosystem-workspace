"""
Trainer Worker — ARQ Worker Entry Point

รัน Worker:
    python worker.py

Worker จะรอรับ Job จาก Redis Queue และประมวลผลตาม Schedule ที่กำหนด
"""

import logging
import os

from arq import run_worker
from arq.connections import RedisSettings

from tasks.train_token_classifier import train_token_classifier

# ── Logging Setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trainer-worker")


async def startup(ctx: dict) -> None:
    """รันเมื่อ Worker เริ่มต้น"""
    logger.info("🚀 Trainer Worker started — Waiting for jobs...")
    logger.info(f"   Redis: {os.getenv('REDIS_URL', 'redis://redis:6379/0')}")
    logger.info(f"   MinIO: {os.getenv('MINIO_ENDPOINT', 'minio:9000')}")

    # ตรวจสอบ GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"   GPU:   ✅ {gpu_name} (CUDA {torch.version.cuda})")
        else:
            logger.warning("   GPU:   ⚠️  CUDA not available — using CPU")
    except ImportError:
        logger.warning("   GPU:   ⚠️  PyTorch not found")


async def shutdown(ctx: dict) -> None:
    """รันเมื่อ Worker กำลังหยุด"""
    logger.info("🛑 Trainer Worker shutting down...")


class WorkerSettings:
    """การตั้งค่า ARQ Worker"""

    # ── Functions ที่ Worker รู้จัก (ต้องตรงกับชื่อที่ enqueue จาก FastAPI) ──
    functions = [train_token_classifier]

    # ── Redis Connection ──
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://redis:6379/0")
    )

    # ── Lifecycle Hooks ──
    on_startup = startup
    on_shutdown = shutdown

    # ── Job Settings ──
    max_jobs = 1          # เทรนทีละ 1 งาน (ป้องกัน GPU Out-of-Memory)
    job_timeout = 18000   # 5 ชั่วโมง (วินาที) — timeout สำหรับการเทรน
    keep_result = 86400   # เก็บผลลัพธ์ไว้ใน Redis 24 ชั่วโมง
    poll_delay = 5.0      # ตรวจสอบ Queue ทุก 5 วินาที


if __name__ == "__main__":
    run_worker(WorkerSettings)
