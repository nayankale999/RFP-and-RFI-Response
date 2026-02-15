from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "RFP Automation API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://rfp_user:rfp_dev_password@localhost:5432/rfp_automation"
    database_sync_url: str = "postgresql://rfp_user:rfp_dev_password@localhost:5432/rfp_automation"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "rfp-documents"
    minio_secure: bool = False

    # AI Services
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"

    # Auth
    jwt_secret: str = "dev-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480

    # Processing
    max_chunk_tokens: int = 4000
    chunk_overlap_tokens: int = 200
    confidence_threshold: float = 0.7
    max_upload_size_mb: int = 100

    # Google Sheets (optional)
    google_service_account_json: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
