"""
FastAPI Application — Main Entry Point with Comprehensive OpenAPI Metadata

รันเซิร์ฟเวอร์:
    uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

เอกสาร API (API Documentation):
    Swagger UI: http://localhost:8000/docs
    ReDoc UI:   http://localhost:8000/redoc
    OpenAPI JSON Schema: http://localhost:8000/openapi.json
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import Base, engine
from core.minio_client import ensure_bucket

# ── Import Feature Routers ──
from app.features.auth.router import router as auth_router
from app.features.profile.router import router as profile_router
from app.features.system.router import router as system_router
from app.features.storage.router import router as storage_router
from app.features.tasks.router import router as tasks_router
from app.features.annotation.router import router as annotation_router
from app.features.training.router import router as training_router
from app.features.inference.router import router as inference_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / Shutdown Lifecycle Events
    """
    # ── Startup ──
    import app.features.auth.models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"⚠️ Database setup warning: {e}")

    try:
        ensure_bucket(settings.minio_profile_bucket)
        print(f"✅ MinIO bucket '{settings.minio_profile_bucket}' ready")
    except Exception as e:
        print(f"⚠️ MinIO bucket setup warning: {e}")

    yield

    # ── Shutdown ──
    print("🛑 Application shutting down")


# ── OpenAPI Tags Metadata (FastAPI Metadata Tutorial) ──
tags_metadata = [
    {
        "name": "Health",
        "description": "API สำหรับตรวจสอบสถานะเบื้องต้นของแอปพลิเคชัน (Health Check)",
    },
    {
        "name": "System & Infrastructure",
        "description": "API สำหรับตรวจสอบสถานะการเชื่อมต่อบริการทั้งหมดในระบบ (PostgreSQL, MinIO, Redis, Label Studio)",
    },
    {
        "name": "Authentication",
        "description": "ระบบยืนยันตัวตน สมาชิก Sign-up, Login ออกแบบในรูปแบบ Stateless JWT Bearer Token Pair พร้อม Token Rotation",
    },
    {
        "name": "Profile",
        "description": "ระบบจัดการโปรไฟล์ผู้ใช้งาน อัปโหลดและจัดการรูปภาพโปรไฟล์ผ่าน MinIO S3 Object Storage",
    },
    {
        "name": "MinIO Object Storage",
        "description": "บริการจัดการไฟล์วัตถุ (Object Storage) การเรียกดู Bucket, รายการไฟล์ และการสร้าง Presigned Download URL",
    },
    {
        "name": "Redis Cache & ARQ Tasks",
        "description": "บริการจัดเก็บข้อมูลชั่วคราว (Key-Value Cache) และระบบคิวงานประมวลผลเบื้องหลังแบบ Asynchronous (ARQ Queue)",
    },
    {
        "name": "Label Studio Annotation",
        "description": "บริการเชื่อมต่อกับแพลตฟอร์มติดฉลากข้อมูล AI/ML (Data Labeling & Annotation Platform)",
    },
    {
        "name": "ML Training Pipeline",
        "description": (
            "ระบบ ML Training Pipeline — ดาวน์โหลด Dataset จาก HuggingFace, "
            "จัดเก็บใน MinIO และสั่งเทรน Token Classification Model แบบ Scheduled Queue ผ่าน ARQ + Redis"
        ),
    },
    {
        "name": "NER Inference",
        "description": (
            "ระบบ NER Inference — ส่งข้อความเข้า Queue เพื่อทำ Named Entity Recognition "
            "โดย Inference Worker โหลด Trained Model จาก MLflow Model Registry"
        ),
    },
]

# ── สร้าง FastAPI app พร้อม Metadata ครบถ้วน ──
app = FastAPI(
    title="AI Ecosystem Multi-Service Core API",
    description=(
        "## ระบบบริการส่วนหลัง AI Ecosystem (Backend Multi-Service Architecture)\n\n"
        "แอปพลิเคชันนี้ทำหน้าที่เป็น **Core Backend Server** สำหรับเชื่อมต่อและให้บริการผ่านองค์ประกอบต่างๆ:\n\n"
        "* **Relational Database**: PostgreSQL สำหรับเก็บข้อมูลบัญชีผู้ใช้และ Metadata\n"
        "* **Cloud Object Storage**: MinIO (S3 Compatible) สำหรับเก็บไฟล์สื่อและรูปภาพ\n"
        "* **In-Memory Cache & Message Broker**: Redis & ARQ สำหรับระบบแคชและคิวงานเบื้องหลัง\n"
        "* **Data Annotation Platform**: Label Studio สำหรับจัดการชุดข้อมูลและติดฉลากสำหรับ AI/ML\n\n"
        "--- \n"
        "### 🔐 การยืนยันตัวตน (Authentication)\n"
        "ปุ่ม **Authorize** ด้านบนสุดใช้ใส่ค่า **Bearer Access Token** ที่ได้จากการเรียก API `/auth/login`"
    ),
    version="1.0.0",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "AI Ecosystem Developer Team",
        "url": "https://example.com/support",
        "email": "dev-team@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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

# ── Register Routers ──
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(storage_router)
app.include_router(tasks_router)
app.include_router(annotation_router)
app.include_router(training_router)
app.include_router(inference_router)


# ── Observability: Prometheus Metrics ──
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
    ).instrument(app).expose(app, endpoint="/metrics", tags=["System & Infrastructure"])
    print("✅ Prometheus metrics enabled at /metrics")
except Exception as e:
    print(f"⚠️ Prometheus instrumentator warning: {e}")


# ── Observability: OpenTelemetry Distributed Tracing ──
try:
    import os
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    service_name = os.getenv("OTEL_SERVICE_NAME", "fastapi-core")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    print(f"✅ OpenTelemetry tracing enabled (target: {otlp_endpoint}, service: {service_name})")
except Exception as e:
    print(f"⚠️ OpenTelemetry tracing warning: {e}")


# ── Root Health Check ──
@app.get("/", tags=["Health"], summary="Root Health Endpoint")
def root():
    """Health check endpoint ระดับรากของเซิร์ฟเวอร์"""
    return {
        "status": "ok",
        "service": "AI Ecosystem Multi-Service Core API",
        "version": "1.0.0",
        "docs_swagger": "/docs",
        "docs_redoc": "/redoc",
        "openapi_json": "/openapi.json",
        "metrics_prometheus": "/metrics",
    }
