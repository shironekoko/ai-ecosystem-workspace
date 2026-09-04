"""
Training Feature — Router (API Endpoints)

Endpoints:
    POST /training/dataset/download  — ดาวน์โหลด Dataset จาก HuggingFace → MinIO
    POST /training/enqueue           — เข้าคิวสั่งเทรน (Scheduled)
    GET  /training/jobs/{job_id}     — ตรวจสอบสถานะ Job
"""

import uuid
from datetime import datetime, timezone

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException, status

from core.config import settings
from app.features.training.schemas import (
    DownloadDatasetRequest,
    DownloadDatasetResponse,
    EnqueueTrainingRequest,
    EnqueueTrainingResponse,
    JobStatusResponse,
)
from app.features.training.service import download_dataset_to_minio

router = APIRouter(prefix="/training", tags=["ML Training Pipeline"])


# ─────────────────────────────────────────────
# POST /training/dataset/download
# ─────────────────────────────────────────────
@router.post(
    "/dataset/download",
    response_model=DownloadDatasetResponse,
    summary="ดาวน์โหลด Dataset จาก HuggingFace → เก็บใน MinIO",
    description="""
ดาวน์โหลด Dataset จาก HuggingFace Hub แล้วบันทึกเป็น Parquet files ใน MinIO

**Bucket ที่ใช้เก็บ:** `datasets/{dataset_name}/{split}.parquet`

**Dataset ที่รองรับ (Token Classification):**
- `conll2003` — Named Entity Recognition (NER) มาตรฐาน
""",
)
def download_dataset(body: DownloadDatasetRequest):
    """ดาวน์โหลด Dataset จาก HuggingFace Hub และเก็บใน MinIO"""
    try:
        uploaded = download_dataset_to_minio(
            dataset_name=body.dataset_name,
            splits=body.splits,
        )
        return DownloadDatasetResponse(
            dataset_name=body.dataset_name,
            splits_uploaded=uploaded,
            bucket="datasets",
            message=f"ดาวน์โหลดและอัปโหลด Dataset '{body.dataset_name}' สำเร็จ ({len(uploaded)} files)",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถดาวน์โหลด Dataset ได้: {str(e)}",
        )


# ─────────────────────────────────────────────
# POST /training/enqueue
# ─────────────────────────────────────────────
@router.post(
    "/enqueue",
    response_model=EnqueueTrainingResponse,
    summary="เข้าคิวสั่งเทรน Model (Scheduled Queue)",
    description="""
ส่งคำสั่งเทรน Token Classification Model เข้า ARQ Task Queue พร้อมกำหนดเวลาเริ่มงาน

**การทำงาน:**
1. รับพารามิเตอร์การเทรน + `scheduled_at` (วันเวลาที่ต้องการให้เริ่ม)
2. ส่ง Job เข้า Redis Queue ด้วย `_defer_until=scheduled_at`
3. Trainer Worker จะตรวจสอบ Queue และเริ่มทำงานเมื่อถึงเวลาที่กำหนดเท่านั้น

**Trainer Worker จะทำ:**
- โหลด Dataset จาก MinIO
- Tokenize + Align Labels ตาม HuggingFace Chapter 7
- เทรนด้วย HuggingFace Trainer API (รองรับ GPU)
- บันทึก Training Log → `training-logs/{job_id}/training_log.json`
- บันทึก Model → `models/{job_id}/`
""",
)
async def enqueue_training(body: EnqueueTrainingRequest):
    """
    เข้าคิวสั่งเทรน Model พร้อมกำหนดเวลาเริ่มต้น

    ใช้ ARQ `_defer_until` เพื่อให้ Worker เริ่มงาน ณ เวลาที่กำหนด
    """
    job_id = str(uuid.uuid4())

    # ── แปลง scheduled_at เป็น UTC (ARQ ต้องการ timezone-aware datetime) ──
    scheduled_at_utc = body.scheduled_at.astimezone(timezone.utc)
    now_utc = datetime.now(timezone.utc)

    # ── ตรวจสอบว่า scheduled_at เป็นเวลาในอนาคต ──
    # ARQ จะ error ถ้า _defer_until เป็นเวลาในอดีต (คำนวณ TTL ออกมาติดลบ)
    is_future = scheduled_at_utc > now_utc

    try:
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await create_pool(redis_settings)

        if is_future:
            # ── กำหนดเวลาล่วงหน้า → ใส่ _defer_until ──
            job = await arq_pool.enqueue_job(
                "train_token_classifier",
                job_id=job_id,
                dataset_name=body.dataset_name,
                model_name=body.model_name,
                num_epochs=body.num_epochs,
                learning_rate=body.learning_rate,
                _defer_until=scheduled_at_utc,
                _job_id=job_id,
            )
            status_msg = "scheduled"
        else:
            # ── เวลาผ่านไปแล้ว / ทันที → ไม่ใส่ _defer_until (เริ่มได้เลย) ──
            job = await arq_pool.enqueue_job(
                "train_token_classifier",
                job_id=job_id,
                dataset_name=body.dataset_name,
                model_name=body.model_name,
                num_epochs=body.num_epochs,
                learning_rate=body.learning_rate,
                _job_id=job_id,
            )
            status_msg = "queued"

        return EnqueueTrainingResponse(
            job_id=job_id,
            status=status_msg,
            dataset_name=body.dataset_name,
            model_name=body.model_name,
            scheduled_at=body.scheduled_at,
            message=(
                f"เข้าคิวสั่งเทรนเรียบร้อย — "
                f"Trainer Worker จะเริ่มทำงานเมื่อถึง {body.scheduled_at.isoformat()}"
                if is_future
                else f"เข้าคิวเรียบร้อย — Trainer Worker จะเริ่มทำงานทันที (job_id: {job_id})"
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถส่งงานเข้า Queue ได้: {str(e)}",
        )


# ─────────────────────────────────────────────
# GET /training/jobs/{job_id}
# ─────────────────────────────────────────────
@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="ตรวจสอบสถานะ Training Job",
    description="ดึงสถานะและผลลัพธ์ของ Training Job จาก ARQ Redis Queue",
)
async def get_job_status(job_id: str):
    """ตรวจสอบสถานะของ Training Job ด้วย Job ID"""
    try:
        from arq.jobs import Job, JobStatus

        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await create_pool(redis_settings)

        job = Job(job_id=job_id, redis=arq_pool)
        job_status = await job.status()
        job_info = await job.info()

        result = None
        if job_status == JobStatus.complete:
            result = await job.result()

        return JobStatusResponse(
            job_id=job_id,
            status=job_status.value if job_status else "not_found",
            result=result if isinstance(result, dict) else None,
            enqueue_time=job_info.enqueue_time if job_info else None,
            start_time=job_info.start_time if job_info else None,
            finish_time=job_info.finish_time if job_info else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถตรวจสอบสถานะ Job ได้: {str(e)}",
        )
