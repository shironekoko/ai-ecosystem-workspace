"""
Inference Feature — Router (API Endpoints)

Endpoints:
    POST /predict               — ส่งข้อความเข้า Queue เพื่อทำ NER Prediction
    GET  /predict/jobs/{job_id} — ตรวจสอบผลลัพธ์ Prediction ด้วย Job ID
"""

import json
import uuid

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job
from fastapi import APIRouter, HTTPException, status

from core.config import settings
from app.features.inference.schemas import (
    PredictRequest,
    PredictResponse,
    PredictResultResponse,
)

router = APIRouter(prefix="/predict", tags=["NER Inference"])


# ─────────────────────────────────────────────
# POST /predict
# ─────────────────────────────────────────────
@router.post(
    "",
    response_model=PredictResponse,
    summary="ส่งข้อความเข้า Queue เพื่อทำ NER Prediction",
    description="""
ส่งข้อความภาษาอังกฤษเข้า Redis Queue เพื่อให้ Inference Worker ทำ Named Entity Recognition

**การทำงาน:**
1. รับข้อความ + เวอร์ชันโมเดล
2. ส่ง Job เข้า Redis Queue `arq:inference`
3. Inference Worker จะดึง Job ไปประมวลผล
4. ใช้ `GET /predict/jobs/{job_id}` เพื่อดึงผลลัพธ์

**Inference Worker จะทำ:**
- โหลด Trained Model จาก MLflow Model Registry
- ทำ NER Prediction ด้วย HuggingFace Pipeline
- ส่งผลลัพธ์กลับผ่าน Redis
""",
)
async def enqueue_prediction(body: PredictRequest):
    """
    Enqueue NER Prediction Job เข้า Redis Queue

    Inference Worker จะรับ Job ไปประมวลผลและเก็บผลลัพธ์ใน Redis
    """
    job_id = str(uuid.uuid4())

    try:
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await create_pool(redis_settings)

        # ส่ง Job เข้า Queue 'arq:inference' (แยกจาก training queue)
        job = await arq_pool.enqueue_job(
            "predict_ner",
            job_id=job_id,
            text=body.text,
            model_version=body.model_version,
            _job_id=job_id,
            _queue_name="arq:inference",
        )

        return PredictResponse(
            job_id=job_id,
            status="queued",
            message=f"ส่งคำสั่ง Predict เข้าคิวเรียบร้อย — ใช้ GET /predict/jobs/{job_id} เพื่อดูผลลัพธ์",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถส่งงานเข้า Queue ได้: {str(e)}",
        )


# ─────────────────────────────────────────────
# GET /predict/jobs/{job_id}
# ─────────────────────────────────────────────
@router.get(
    "/jobs/{job_id}",
    response_model=PredictResultResponse,
    summary="ตรวจสอบผลลัพธ์ Prediction ด้วย Job ID",
    description="""
ดึงผลลัพธ์ของ NER Prediction Job ที่ส่งไปก่อนหน้านี้

**สถานะที่เป็นไปได้:**
- `pending` — Job กำลังอยู่ในคิวหรือกำลังประมวลผล
- `completed` — ประมวลผลเสร็จ มีผลลัพธ์ Entities
- `failed` — เกิดข้อผิดพลาดระหว่างประมวลผล
- `not_found` — ไม่พบ Job ID นี้ในระบบ
""",
)
async def get_prediction_result(job_id: str):
    """
    ดึงผลลัพธ์ Prediction จาก Redis ด้วย Job ID
    """
    try:
        from arq.jobs import Job, JobStatus

        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await create_pool(redis_settings)

        # ── ค้นหา Job จาก ARQ ──
        job = Job(job_id=job_id, redis=arq_pool)
        job_status = await job.status()

        if job_status == JobStatus.not_found or job_status is None:
            return PredictResultResponse(
                job_id=job_id,
                status="not_found",
            )

        if job_status == JobStatus.complete:
            result = await job.result()
            if isinstance(result, dict):
                return PredictResultResponse(
                    job_id=result.get("job_id", job_id),
                    status=result.get("status", "completed"),
                    text=result.get("text"),
                    model_version=result.get("model_version"),
                    entities=result.get("entities"),
                    entity_count=result.get("entity_count"),
                    error=result.get("error"),
                )

        # Job กำลังรอในคิว หรือ กำลังประมวลผล
        return PredictResultResponse(
            job_id=job_id,
            status=job_status.value if hasattr(job_status, "value") else str(job_status),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถดึงผลลัพธ์ได้: {str(e)}",
        )
