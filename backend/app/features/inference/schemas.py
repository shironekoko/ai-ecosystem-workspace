"""
Inference Feature — Pydantic Schemas

Request/Response Models สำหรับ Inference API Endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional


class PredictRequest(BaseModel):
    """Request Body สำหรับ POST /predict"""

    text: str = Field(
        ...,
        description="ข้อความภาษาอังกฤษที่ต้องการตรวจหา Named Entities",
        examples=["Elon Musk visited the United Nations headquarters in New York."],
    )
    model_version: str = Field(
        default="latest",
        description="เวอร์ชันของโมเดลจาก MLflow Model Registry ('latest', '1', '2', ...)",
    )


class PredictResponse(BaseModel):
    """Response สำหรับ POST /predict — ตอบกลับ Job ID ที่ถูก Enqueue"""

    job_id: str = Field(..., description="UUID ของ Job สำหรับตรวจสอบผลลัพธ์")
    status: str = Field(..., description="สถานะ Job ('queued')")
    message: str = Field(..., description="ข้อความอธิบาย")


class EntityResult(BaseModel):
    """ข้อมูล Entity ที่ตรวจเจอ"""

    entity_group: str = Field(..., description="ประเภท Entity เช่น PER, ORG, LOC, MISC")
    word: str = Field(..., description="คำหรือวลีที่เป็น Entity")
    score: float = Field(..., description="ค่าความมั่นใจ (0.0 - 1.0)")
    start: int = Field(..., description="ตำแหน่งเริ่มต้นในข้อความ")
    end: int = Field(..., description="ตำแหน่งสิ้นสุดในข้อความ")


class PredictResultResponse(BaseModel):
    """Response สำหรับ GET /predict/jobs/{job_id} — ผลลัพธ์ Prediction"""

    job_id: str = Field(..., description="UUID ของ Job")
    status: str = Field(..., description="สถานะ ('pending', 'completed', 'failed', 'not_found')")
    text: Optional[str] = Field(None, description="ข้อความต้นฉบับ")
    model_version: Optional[str] = Field(None, description="เวอร์ชันโมเดลที่ใช้")
    entities: Optional[list[EntityResult]] = Field(None, description="รายการ Entities ที่ตรวจเจอ")
    entity_count: Optional[int] = Field(None, description="จำนวน Entities ทั้งหมด")
    error: Optional[str] = Field(None, description="ข้อผิดพลาด (ถ้ามี)")
