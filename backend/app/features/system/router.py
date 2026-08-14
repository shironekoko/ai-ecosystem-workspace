"""
System Router — API endpoints สำหรับตรวจสอบสถานะของ Components ทั้งหมดในระบบ
(PostgreSQL, MinIO, Redis, Label Studio)
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db
from core.config import settings
from core.minio_client import get_minio_client
import redis
from label_studio_sdk.client import LabelStudio

router = APIRouter(prefix="/system", tags=["System & Infrastructure"])


class ComponentStatus(BaseModel):
    name: str = Field(..., example="PostgreSQL")
    status: str = Field(..., example="online")
    details: str = Field(..., example="Connected successfully")


class SystemHealthResponse(BaseModel):
    overall_status: str = Field(..., example="healthy")
    components: list[ComponentStatus]


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="ตรวจสอบสถานะความพร้อมของบริการทั้งหมด (System Health Check)",
    response_description="คืนค่าสถานะการเชื่อมต่อของ PostgreSQL, MinIO, Redis และ Label Studio",
)
def check_system_health(db: Session = Depends(get_db)):
    """
    **การตรวจสอบสถานะการเชื่อมต่อ (Health Check)**:
    - **PostgreSQL**: ส่งคำสั่ง `SELECT 1` ผ่าน SQLAlchemy
    - **MinIO**: เรียกคำสั่ง `list_buckets()` เพื่อตรวจสอบ S3 API
    - **Redis**: สื่อสารคำสั่ง `PING` ผ่าน Redis client
    - **Label Studio**: ตรวจสอบการเชื่อมต่อ API ของ Label Studio SDK
    """
    components = []
    all_healthy = True

    # 1. PostgreSQL Check
    try:
        db.execute(text("SELECT 1"))
        components.append(
            ComponentStatus(
                name="PostgreSQL",
                status="online",
                details="Database connection operational",
            )
        )
    except Exception as e:
        all_healthy = False
        components.append(
            ComponentStatus(
                name="PostgreSQL",
                status="offline",
                details=f"Connection failed: {str(e)}",
            )
        )

    # 2. MinIO Check
    try:
        minio_client = get_minio_client()
        minio_client.list_buckets()
        components.append(
            ComponentStatus(
                name="MinIO Object Storage",
                status="online",
                details=f"Connected to {settings.minio_endpoint}",
            )
        )
    except Exception as e:
        all_healthy = False
        components.append(
            ComponentStatus(
                name="MinIO Object Storage",
                status="offline",
                details=f"Connection failed: {str(e)}",
            )
        )

    # 3. Redis Check
    try:
        r = redis.Redis.from_url(settings.redis_url)
        if r.ping():
            components.append(
                ComponentStatus(
                    name="Redis Cache & Queue",
                    status="online",
                    details="Ping successful",
                )
            )
        else:
            all_healthy = False
            components.append(
                ComponentStatus(
                    name="Redis Cache & Queue",
                    status="offline",
                    details="Ping returned False",
                )
            )
    except Exception as e:
        all_healthy = False
        components.append(
            ComponentStatus(
                name="Redis Cache & Queue",
                status="offline",
                details=f"Connection failed: {str(e)}",
            )
        )

    # 4. Label Studio Check
    try:
        ls = LabelStudio(
            base_url=settings.label_studio_url,
            api_key=settings.label_studio_api_key,
        )
        _ = list(ls.projects.list())
        components.append(
            ComponentStatus(
                name="Label Studio",
                status="online",
                details=f"Connected to {settings.label_studio_url}",
            )
        )
    except Exception as e:
        components.append(
            ComponentStatus(
                name="Label Studio",
                status="degraded/offline",
                details=f"Connection check failed: {str(e)}",
            )
        )

    return SystemHealthResponse(
        overall_status="healthy" if all_healthy else "degraded",
        components=components,
    )
