"""
FastAPI Application — Entry Point

รัน: uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import Base, engine
from core.minio_client import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / Shutdown events

    Startup:
    - สร้าง database tables (ถ้ายังไม่มี)
    - สร้าง MinIO bucket สำหรับ profile images (ถ้ายังไม่มี)
    """
    # ── Startup ──
    # Import models เพื่อให้ Base.metadata รู้จัก tables ทั้งหมด
    import app.features.auth.models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created")
    except Exception as e:
        print(f"Database setup failed (server may not be ready): {e}")

    try:
        ensure_bucket(settings.minio_profile_bucket)
        print(f"MinIO bucket '{settings.minio_profile_bucket}' ready")
    except Exception as e:
        print(f"MinIO bucket setup failed (server may not be ready): {e}")

    yield

    # ── Shutdown ──
    print("Application shutting down")


# ── สร้าง FastAPI app ──
app = FastAPI(
    title="AI Ecosystem — Auth API",
    description=(
        "ระบบ Authentication & Profile Management\n\n"
        "- **Sign-up**: สมัครสมาชิก\n"
        "- **Login**: เข้าสู่ระบบ → ได้ JWT token\n"
        "- **Logout**: ออกจากระบบ\n"
        "- **Profile**: ดู/แก้ไขโปรไฟล์ + รูปโปรไฟล์ผ่าน MinIO\n\n"
        "Use the **Authorize** button above to enter your Bearer token for protected endpoints"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ──
from app.features.auth.router import router as auth_router
from app.features.profile.router import router as profile_router

app.include_router(auth_router)
app.include_router(profile_router)


# ── Root Endpoint ──
@app.get("/", tags=["Health"])
def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AI Ecosystem Auth API",
        "version": "1.0.0",
        "docs": "/docs",
    }
