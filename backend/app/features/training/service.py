"""
Training Feature — Service Layer
Business Logic: ดาวน์โหลด Dataset จาก HuggingFace และส่งงานเข้า ARQ Queue
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from minio import Minio

from core.config import settings

logger = logging.getLogger(__name__)

BUCKET_DATASETS = "datasets"


def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket(client: Minio, bucket_name: str) -> None:
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        logger.info(f"✅ Created MinIO bucket: {bucket_name}")


def download_dataset_to_minio(
    dataset_name: str,
    splits: list[str],
) -> list[str]:
    """
    ดาวน์โหลด Dataset จาก HuggingFace Hub แล้วเก็บใน MinIO เป็น Parquet files

    Args:
        dataset_name: ชื่อ Dataset บน HuggingFace เช่น "conll2003"
        splits: รายการ splits ที่ต้องการ เช่น ["train", "validation", "test"]

    Returns:
        รายการ object names ที่อัปโหลดสำเร็จ
    """
    # Import datasets ที่นี่เพื่อไม่ให้ FastAPI ต้องติดตั้ง HuggingFace dependencies
    # (FastAPI Container ไม่มี transformers/datasets)
    try:
        import datasets as hf_datasets
    except ImportError:
        raise RuntimeError(
            "ไม่พบ 'datasets' library — "
            "กรุณาติดตั้งด้วย: uv add datasets"
        )

    # จัดการ Dataset Name Alias (เนื่องจาก datasets v3+ ยกเลิกการรัน .py scripts บน Hub)
    # ถ้าผู้ใช้ส่ง "conll2003" ให้โหลดจาก repo parquet มาตรฐาน "lhoestq/conll2003"
    hf_dataset_repo = dataset_name
    if dataset_name.lower() in ["conll2003", "conll_2003"]:
        hf_dataset_repo = "lhoestq/conll2003"

    logger.info(f"📥 Downloading '{hf_dataset_repo}' (alias for '{dataset_name}') from HuggingFace Hub...")
    try:
        raw_dataset = hf_datasets.load_dataset(hf_dataset_repo)
    except Exception as e:
        # Fallback กรณี repo เดิมมี script หรือ error
        logger.warning(f"⚠️ Primary load failed: {e}. Trying fallback 'lhoestq/conll2003'...")
        raw_dataset = hf_datasets.load_dataset("lhoestq/conll2003")

    client = get_minio_client()
    ensure_bucket(client, BUCKET_DATASETS)

    uploaded_objects = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for split_name in splits:
            if split_name not in raw_dataset:
                logger.warning(f"⚠️  Split '{split_name}' not found in dataset, skipping")
                continue

            split_data = raw_dataset[split_name]
            local_path = os.path.join(tmp_dir, f"{split_name}.parquet")

            # บันทึกเป็น Parquet (รักษา Schema รวมถึง ClassLabel features)
            split_data.to_parquet(local_path)
            logger.info(f"   Saved {split_name}: {len(split_data):,} rows → {local_path}")

            # อัปโหลดไป MinIO: datasets/{dataset_name}/{split}.parquet
            object_name = f"{dataset_name}/{split_name}.parquet"
            client.fput_object(BUCKET_DATASETS, object_name, local_path)
            uploaded_objects.append(object_name)
            logger.info(f"📤 Uploaded: {object_name}")

    logger.info(f"✅ Dataset '{dataset_name}' stored in MinIO ({len(uploaded_objects)} files)")
    return uploaded_objects
