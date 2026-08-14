"""
Storage Router — API endpoints สำหรับจัดการ MinIO Object Storage ผ่าน MinIO Library SDK
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from core.config import settings
from core.minio_client import get_minio_client, get_presigned_url, list_objects

router = APIRouter(prefix="/storage", tags=["MinIO Object Storage"])


class BucketItem(BaseModel):
    name: str = Field(..., example="profile-images")
    creation_date: str = Field(..., example="2026-08-13T12:00:00Z")


class ObjectItem(BaseModel):
    name: str = Field(..., example="avatars/user-123.jpg")
    size: int = Field(..., example=102400)
    last_modified: str


class PresignedUrlRequest(BaseModel):
    bucket_name: str = Field(..., example="profile-images")
    object_name: str = Field(..., example="avatars/user-123.jpg")
    expires_hours: int = Field(default=1, ge=1, le=24, description="จำนวนชั่วโมงที่ URL สามารถใช้งานได้")


class PresignedUrlResponse(BaseModel):
    bucket_name: str
    object_name: str
    presigned_url: str
    expires_in_hours: int


@router.get(
    "/buckets",
    response_model=list[BucketItem],
    summary="เรียกดูรายการ Bucket ทั้งหมดใน MinIO Storage",
    response_description="คืนค่ารายชื่อ Bucket และวันที่สร้าง",
)
def list_minio_buckets():
    """ดึงรายการ Buckets ทั้งหมดที่มีอยู่ใน MinIO Object Storage"""
    try:
        client = get_minio_client()
        buckets = client.list_buckets()
        return [
            BucketItem(
                name=b.name,
                creation_date=b.creation_date.isoformat() if b.creation_date else "",
            )
            for b in buckets
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการดึงรายการ Buckets จาก MinIO: {str(e)}",
        )


@router.get(
    "/objects",
    response_model=list[ObjectItem],
    summary="เรียกดูรายการไฟล์ใน Bucket (List Objects)",
)
def list_bucket_objects(
    bucket_name: str = Query(..., description="ชื่อ Bucket ที่ต้องการค้นหา"),
    prefix: str | None = Query(None, description="Prefix เส้นทางโฟลเดอร์ (ถ้ามี)"),
):
    """เรียกดูรายชื่อวัตถุ/ไฟล์ทั้งหมดใน Bucket ที่ระบุ"""
    try:
        objs = list_objects(bucket_name, prefix=prefix)
        return [
            ObjectItem(
                name=obj["name"],
                size=obj["size"],
                last_modified=obj["last_modified"].isoformat() if obj["last_modified"] else "",
            )
            for obj in objs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถดึงข้อมูลไฟล์ใน Bucket '{bucket_name}': {str(e)}",
        )


@router.post(
    "/presigned-url",
    response_model=PresignedUrlResponse,
    summary="สร้าง Presigned URL สำหรับดาวน์โหลดไฟล์แบบจำกัดเวลา",
)
def generate_object_presigned_url(body: PresignedUrlRequest):
    """สร้างลิงก์ดาวน์โหลดไฟล์ชั่วคราวผ่าน MinIO Presigned GET Object API"""
    try:
        url = get_presigned_url(
            bucket_name=body.bucket_name,
            object_name=body.object_name,
            expires=timedelta(hours=body.expires_hours),
        )
        return PresignedUrlResponse(
            bucket_name=body.bucket_name,
            object_name=body.object_name,
            presigned_url=url,
            expires_in_hours=body.expires_hours,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ไม่สามารถสร้าง Presigned URL ได้: {str(e)}",
        )
