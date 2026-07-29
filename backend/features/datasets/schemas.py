from pydantic import BaseModel

class UploadResponse(BaseModel):
    filename: str
    bucket_name: str
    message: str