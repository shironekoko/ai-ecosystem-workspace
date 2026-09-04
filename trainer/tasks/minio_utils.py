"""
MinIO Utilities สำหรับ Trainer Worker
— Upload / Download Dataset และ Model
"""

import logging
import os
from pathlib import Path

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

# ── MinIO Bucket Names ──
BUCKET_DATASETS = "datasets"
BUCKET_MODELS = "models"
BUCKET_LOGS = "training-logs"


def get_minio_client() -> Minio:
    """สร้าง MinIO Client จาก Environment Variables"""
    return Minio(
        endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "miniouser"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "miniopassword"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )


def ensure_bucket(client: Minio, bucket_name: str) -> None:
    """สร้าง Bucket ถ้ายังไม่มี"""
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        logger.info(f"✅ Created bucket: {bucket_name}")


def download_dataset_from_minio(
    dataset_name: str,
    local_dir: str,
    splits: list[str] | None = None,
) -> Path:
    """
    ดาวน์โหลด Dataset Parquet files จาก MinIO ไปเก็บไว้ใน local_dir

    Args:
        dataset_name: ชื่อ Dataset เช่น "conll2003"
        local_dir: โฟลเดอร์ชั่วคราวที่ดาวน์โหลดไปเก็บ
        splits: รายการ splits เช่น ["train", "validation", "test"]

    Returns:
        Path ของโฟลเดอร์ที่เก็บ parquet files
    """
    if splits is None:
        splits = ["train", "validation", "test"]

    client = get_minio_client()
    dest = Path(local_dir) / dataset_name
    dest.mkdir(parents=True, exist_ok=True)

    for split in splits:
        object_name = f"{dataset_name}/{split}.parquet"
        local_path = dest / f"{split}.parquet"
        try:
            client.fget_object(BUCKET_DATASETS, object_name, str(local_path))
            logger.info(f"📥 Downloaded: {object_name} → {local_path}")
        except S3Error as e:
            logger.warning(f"⚠️  Cannot download {object_name}: {e}")

    return dest


def upload_model_to_minio(job_id: str, model_dir: str) -> list[str]:
    """
    อัปโหลดไฟล์ Model ทั้งหมดใน model_dir ขึ้นไปยัง MinIO
    Bucket: models/{job_id}/

    Returns:
        รายการ object names ที่อัปโหลดสำเร็จ
    """
    client = get_minio_client()
    ensure_bucket(client, BUCKET_MODELS)

    model_path = Path(model_dir)
    uploaded = []

    for file_path in model_path.rglob("*"):
        if file_path.is_file():
            # คำนวณ relative path สำหรับใช้เป็น object name
            relative = file_path.relative_to(model_path)
            object_name = f"{job_id}/{relative.as_posix()}"

            client.fput_object(BUCKET_MODELS, object_name, str(file_path))
            uploaded.append(object_name)
            logger.info(f"📤 Uploaded model file: {object_name}")

    logger.info(f"✅ Model uploaded: {len(uploaded)} files → bucket '{BUCKET_MODELS}/{job_id}/'")
    return uploaded


def upload_log_to_minio(job_id: str, log_file_path: str) -> str:
    """
    อัปโหลด Training Log ขึ้น MinIO
    Bucket: training-logs/{job_id}/training_log.json

    Returns:
        object_name ที่อัปโหลด
    """
    client = get_minio_client()
    ensure_bucket(client, BUCKET_LOGS)

    object_name = f"{job_id}/training_log.json"
    client.fput_object(BUCKET_LOGS, object_name, log_file_path)
    logger.info(f"📤 Uploaded training log: {object_name}")
    return object_name
