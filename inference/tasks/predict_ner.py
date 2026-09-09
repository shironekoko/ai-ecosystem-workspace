"""
NER Prediction Task (ARQ Job) — Inference Worker

Flow การทำงาน:
1. รับข้อความ (text) และ model_version จาก Redis Queue
2. โหลด Trained Model จาก MLflow Model Registry
3. ทำ NER Prediction ด้วย HuggingFace Pipeline
4. เซฟผลลัพธ์ลง Redis (ใช้ job_id เป็น Key)
"""

import json
import logging
import os
import tempfile
from pathlib import Path

import mlflow
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline,
)

logger = logging.getLogger(__name__)

# ── Cache สำหรับเก็บ Model ที่โหลดแล้ว (ไม่ต้องโหลดซ้ำทุก Request) ──
_model_cache: dict = {}


def _get_ner_pipeline(model_version: str = "latest"):
    """
    โหลด NER Pipeline จาก MLflow Model Registry
    ใช้ Cache เพื่อไม่ต้องดาวน์โหลดโมเดลซ้ำทุกครั้ง

    Args:
        model_version: เวอร์ชันของโมเดล ("latest", "1", "2", ...)

    Returns:
        HuggingFace Pipeline สำหรับ NER
    """
    cache_key = f"token-classifier:{model_version}"

    if cache_key in _model_cache:
        logger.info(f"♻️ Using cached model: {cache_key}")
        return _model_cache[cache_key]

    logger.info(f"📦 Loading model from MLflow: token-classifier v{model_version}")

    # ── Setup MLflow ──
    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    mlflow.set_tracking_uri(mlflow_tracking_uri)

    # ── ดึงข้อมูล Model จาก MLflow Model Registry ──
    client = mlflow.tracking.MlflowClient()

    if model_version == "latest":
        # ดึง Version ล่าสุด
        versions = client.search_model_versions("name='token-classifier'")
        if not versions:
            raise ValueError("ไม่พบ Model 'token-classifier' ใน MLflow Model Registry — กรุณาเทรนโมเดลก่อน")
        # เรียงตาม version number แล้วเอาตัวล่าสุด
        latest = sorted(versions, key=lambda v: int(v.version), reverse=True)[0]
        run_id = latest.run_id
        version_number = latest.version
        logger.info(f"   Latest version: v{version_number} (run_id: {run_id})")
    else:
        # ดึง Version ที่ระบุ
        model_info = client.get_model_version("token-classifier", model_version)
        run_id = model_info.run_id
        version_number = model_version
        logger.info(f"   Specific version: v{version_number} (run_id: {run_id})")

    # ── ดาวน์โหลด Model Artifacts จาก MLflow ──
    with tempfile.TemporaryDirectory() as tmp_dir:
        artifact_path = mlflow.artifacts.download_artifacts(
            run_id=run_id,
            artifact_path="model",
            dst_path=tmp_dir,
        )
        model_dir = Path(artifact_path)
        logger.info(f"   Downloaded to: {model_dir}")

        # ── โหลด Tokenizer + Model จากไฟล์ที่ดาวน์โหลด ──
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model = AutoModelForTokenClassification.from_pretrained(str(model_dir))

    # ── สร้าง NER Pipeline ──
    ner_pipeline = pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",  # รวม Subwords กลับเป็นคำเดิม
    )

    # เก็บ Cache
    _model_cache[cache_key] = ner_pipeline
    logger.info(f"✅ Model loaded and cached: {cache_key}")

    return ner_pipeline


async def predict_ner(
    ctx: dict,
    job_id: str,
    text: str,
    model_version: str = "latest",
) -> dict:
    """
    ARQ Job Function: ทำ NER Prediction

    Args:
        ctx: ARQ context
        job_id: UUID ของ Job
        text: ข้อความที่ต้องการ Predict
        model_version: เวอร์ชันของโมเดล ("latest", "1", "2", ...)

    Returns:
        dict: ผลลัพธ์การ Predict
    """
    logger.info(f"🔮 [Job {job_id}] Starting NER Prediction")
    logger.info(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    logger.info(f"   Model Version: {model_version}")

    try:
        # ── Step 1: โหลด NER Pipeline ──
        ner_pipeline = _get_ner_pipeline(model_version)

        # ── Step 2: Predict ──
        raw_results = ner_pipeline(text)

        # ── Step 3: แปลงผลลัพธ์ ──
        entities = []
        for entity in raw_results:
            entities.append({
                "entity_group": entity["entity_group"],
                "word": entity["word"],
                "score": round(float(entity["score"]), 4),
                "start": entity["start"],
                "end": entity["end"],
            })

        result = {
            "job_id": job_id,
            "status": "completed",
            "text": text,
            "model_version": model_version,
            "entities": entities,
            "entity_count": len(entities),
        }

        logger.info(f"✅ [Job {job_id}] Prediction complete — Found {len(entities)} entities")
        for ent in entities:
            logger.info(f"   {ent['entity_group']}: \"{ent['word']}\" (score: {ent['score']})")

        return result

    except Exception as e:
        logger.error(f"❌ [Job {job_id}] Prediction failed: {str(e)}")
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
            "text": text,
        }
