"""
Tasks & Redis Router — API endpoints สำหรับจัดการ Cache และ คิวงานเบื้องหลัง (ARQ + Redis)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import redis
from arq import create_pool
from arq.connections import RedisSettings

from core.config import settings

router = APIRouter(prefix="/tasks", tags=["Redis Cache & ARQ Tasks"])


class CacheSetRequest(BaseModel):
    key: str = Field(..., example="system:config:theme")
    value: str = Field(..., example="dark")
    ttl_seconds: int | None = Field(default=300, description="เวลาหมดอายุของข้อมูล (วินาที)")


class CacheResponse(BaseModel):
    key: str
    value: str | None
    is_cached: bool


class EnqueueTaskRequest(BaseModel):
    job_name: str = Field(default="simple_work", example="simple_work")
    job_data: str = Field(..., example="Processing Dataset Batch #102")


class EnqueueTaskResponse(BaseModel):
    job_id: str
    status: str
    message: str


@router.post(
    "/cache",
    response_model=CacheResponse,
    summary="บันทึกข้อมูลเข้า Redis Cache (Set Key-Value with TTL)",
)
def set_redis_cache(body: CacheSetRequest):
    """บันทึกข้อมูล Key-Value ลงใน Redis Cache พร้อมกำหนดเวลาหมดอายุ (TTL)"""
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        if body.ttl_seconds and body.ttl_seconds > 0:
            r.setex(body.key, body.ttl_seconds, body.value)
        else:
            r.set(body.key, body.value)
        return CacheResponse(key=body.key, value=body.value, is_cached=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการบันทึก Redis Cache: {str(e)}",
        )


@router.get(
    "/cache/{key}",
    response_model=CacheResponse,
    summary="ดึงข้อมูลจาก Redis Cache (Get Key-Value)",
)
def get_redis_cache(key: str):
    """อ่านข้อมูลจาก Redis Cache ตาม Key ที่ระบุ"""
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        val = r.get(key)
        return CacheResponse(key=key, value=val, is_cached=val is not None)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการอ่าน Redis Cache: {str(e)}",
        )


@router.post(
    "/enqueue",
    response_model=EnqueueTaskResponse,
    summary="ส่งงานเข้าคิวประมวลผลเบื้องหลัง (Enqueue ARQ Task)",
)
async def enqueue_background_task(body: EnqueueTaskRequest):
    """ส่งคำสั่งเข้าคิวงานเบื้องหลัง (ARQ Task Queue) เพื่อให้ Background Worker ดึงไปประมวลผลแบบ Asynchronous"""
    try:
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await create_pool(redis_settings)
        job = await arq_pool.enqueue_job(body.job_name, body.job_data)
        job_id = job.job_id if job else "unknown"
        return EnqueueTaskResponse(
            job_id=str(job_id),
            status="enqueued",
            message=f"ส่งงาน '{body.job_name}' เข้าคิวงานเรียบร้อยแล้ว",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถส่งงานเข้า ARQ Task Queue ได้: {str(e)}",
        )
