from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve .env from the project root, regardless of CWD
_ENV_FILE = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    # Application
    app_name: str = "Nova Agent Worker"
    app_env: str = "development"
    rules_path: str = "config/rules.json"

    # PostgreSQL Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/nova_pipeline"
    db_pool_min: int = 2
    db_pool_max: int = 10

    # Redis (Streams & Concurrency)
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "trade_doc_tasks"
    redis_consumer_group: str = "trade_doc_worker_group"
    redis_consumer_name: str = "worker-1"

    # Tier 2 Concurrency & Extraction Settings
    max_inflight_llm_calls: int = 5
    extraction_confidence_threshold: float = 0.70
    max_extraction_retries: int = 3

    # Object Storage (MinIO / AWS S3)
    s3_endpoint_url: Optional[str] = "http://localhost:9000"
    s3_access_key_id: Optional[str] = "minioadmin"
    s3_secret_access_key: Optional[str] = "minioadmin"
    s3_bucket_name: str = "trade-documents"
    s3_region: str = "us-east-1"

    # LLM Settings
    default_llm_provider: str = "gemini"
    gemini_model: str = "gemini-2.0-flash"
    gemini_api_key: Optional[str] = None
    mistral_ocr_model: str = "mistral-ocr-latest"
    mistral_extract_model: str = "pixtral-large-latest"
    mistral_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-5"
    anthropic_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
