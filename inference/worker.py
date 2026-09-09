"""
Inference Worker — ARQ Worker Entry Point

รัน Worker:
    python worker.py

Worker จะรอรับ Job การ Predict จาก Redis Queue
โหลด Trained Model จาก MLflow Model Registry แล้วทำ NER Prediction
"""

import logging
import os

from arq import run_worker
from arq.connections import RedisSettings

from tasks.predict_ner import predict_ner

# ── Logging Setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("inference-worker")


async def startup(ctx: dict) -> None:
    """รันเมื่อ Worker เริ่มต้น"""
    logger.info("🚀 Inference Worker started — Waiting for predict jobs...")
    logger.info(f"   Redis:  {os.getenv('REDIS_URL', 'redis://redis:6379/0')}")
    logger.info(f"   MLflow: {os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')}")


async def shutdown(ctx: dict) -> None:
    """รันเมื่อ Worker กำลังหยุด"""
    logger.info("🛑 Inference Worker shutting down...")


class WorkerSettings:
    """การตั้งค่า ARQ Worker สำหรับ Inference"""

    # ── Functions ที่ Worker รู้จัก ──
    functions = [predict_ner]

    # ── Redis Connection ──
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://redis:6379/0")
    )

    # ── ใช้ Queue แยกจาก Trainer Worker ──
    queue_name = "arq:inference"

    # ── Lifecycle Hooks ──
    on_startup = startup
    on_shutdown = shutdown

    # ── Job Settings ──
    max_jobs = 4          # Inference ทำพร้อมกันได้หลาย Job (CPU)
    job_timeout = 300     # 5 นาที timeout สำหรับ Predict
    keep_result = 3600    # เก็บผลลัพธ์ไว้ใน Redis 1 ชั่วโมง
    poll_delay = 1.0      # ตรวจสอบ Queue ทุก 1 วินาที


if __name__ == "__main__":
    run_worker(WorkerSettings)
