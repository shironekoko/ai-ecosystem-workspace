"""
Training Feature — Schemas (Pydantic Models)
"""

from datetime import datetime
from pydantic import BaseModel, Field


class DownloadDatasetRequest(BaseModel):
    dataset_name: str = Field(
        default="conll2003",
        description="ชื่อ Dataset บน HuggingFace เช่น 'conll2003'",
        examples=["conll2003"],
    )
    splits: list[str] = Field(
        default=["train", "validation", "test"],
        description="รายการ Split ที่ต้องการดาวน์โหลด",
    )


class DownloadDatasetResponse(BaseModel):
    dataset_name: str
    splits_uploaded: list[str]
    bucket: str
    message: str


class EnqueueTrainingRequest(BaseModel):
    dataset_name: str = Field(
        default="conll2003",
        description="ชื่อ Dataset ที่เก็บใน MinIO",
        examples=["conll2003"],
    )
    model_name: str = Field(
        default="distilbert-base-uncased",
        description="ชื่อ Pre-trained Model จาก HuggingFace",
        examples=["distilbert-base-uncased", "bert-base-cased"],
    )
    scheduled_at: datetime = Field(
        ...,
        description="วันเวลาที่ต้องการให้ Worker เริ่มเทรน (ISO 8601 format)",
        examples=["2025-01-01T10:30:00+07:00"],
    )
    num_epochs: int = Field(default=3, ge=1, le=10, description="จำนวน Epoch (1-10)")
    learning_rate: float = Field(
        default=2e-5, ge=1e-6, le=1e-3,
        description="Learning Rate",
        examples=[2e-5],
    )


class EnqueueTrainingResponse(BaseModel):
    job_id: str
    status: str
    dataset_name: str
    model_name: str
    scheduled_at: datetime
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    enqueue_time: datetime | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
