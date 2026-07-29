from fastapi import APIRouter, UploadFile, File, HTTPException
from features.datasets import schemas, service
import logging

log = logging.getLogger("FastAPI_Datasets")
router = APIRouter(prefix="/datasets", tags=["Data Management"])

@router.post("/upload", response_model=schemas.UploadResponse)
async def upload_dataset(file: UploadFile = File(...)):
    log.info(f"Receiving file: {file.filename}")
    try:
        bucket = await service.upload_to_minio(file)
        log.info(f"Successfully uploaded {file.filename} to {bucket}")
        return schemas.UploadResponse(
            filename=file.filename,
            bucket_name=bucket,
            message="Upload successful"
        )
    except Exception as e:
        log.error(f"Failed to upload {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))