import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"          # backend/.env
_ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"     # workspace root .env

# ใช้ root .env เป็น primary, backend/.env เป็น fallback
_env_file = str(_ROOT_ENV_PATH) if _ROOT_ENV_PATH.exists() else str(_ENV_PATH)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=_env_file, env_file_encoding="utf-8", extra="ignore"
    )

    # ── Database ──
    database_url: str

    # ── Label Studio ──
    label_studio_url: str
    label_studio_api_key: str
    
    # ── Redis ──
    redis_url: str

    # ── MinIO ──
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool
    minio_profile_bucket: str = "profile-images" # เก็บไว้ตาม Logic เดิมเผื่อใช้งาน

    # ── JWT ──
    jwt_secret_key: str = secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── CORS ──
    cors_origins: list[str] = ["*"]


settings = Settings()  # type: ignore[call-arg]