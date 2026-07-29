from fastapi import FastAPI
from core.logger import setup_logger
from features.datasets.router import router as datasets_router

# เปิดใช้งาน Custom Logger ที่เราสร้างไว้
log = setup_logger("FastAPI_Main")

app = FastAPI(
    title="AI Ecosystem API",
    description="API for managing Datasets, Labeling, and AI Jobs",
    version="1.0.0"
)

# นำ Router ของฟีเจอร์ Datasets มาเชื่อมต่อกับแอปหลัก
app.include_router(datasets_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    log.info("🚀 AI Ecosystem API is starting up...")

@app.get("/")
def root():
    return {"message": "Welcome to AI Ecosystem API"}