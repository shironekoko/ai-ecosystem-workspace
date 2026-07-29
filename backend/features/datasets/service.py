import os
from minio import Minio
from core.config import settings
from fastapi import UploadFile

def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure
    )

async def upload_to_minio(file: UploadFile) -> str:
    client = get_minio_client()
    bucket_name = "profile-bucket"
    
    # สร้าง Bucket ถ้ายังไม่มี
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # บันทึกไฟล์ลงเครื่องชั่วคราวก่อนอัปโหลด
    temp_path = f"tmp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        # อัปโหลดขึ้น MinIO
        client.fput_object(bucket_name, file.filename, temp_path)
    finally:
        # ลบไฟล์ชั่วคราวทิ้งเสมอ (รักษาโครงสร้างโค้ดให้ปลอดภัย)
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return bucket_name