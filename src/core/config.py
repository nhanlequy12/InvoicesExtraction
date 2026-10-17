from pathlib import Path
from typing import List, Optional
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General
    APP_ENV: str = "development"
    APP_NAME: str = "AI Smart Invoice Processing Platform"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "development-secret-key-replace-in-prod"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "smart_invoice_db"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis & Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Storage
    STORAGE_TYPE: str = "local" # local or minio
    LOCAL_STORAGE_PATH: Path = Path("data/uploads")
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "smart-invoices"
    MINIO_SECURE: bool = False

    # External APIs
    TAX_API_BASE_URL: str = "https://api.gdt.gov.vn/v1"
    TAX_API_KEY: str = "mock-key"
    TAX_API_TIMEOUT_SECONDS: float = 5.0

    # Business Rules Paths
    VALIDATION_RULES_PATH: Path = Path("configs/rules/validation_rules.yaml")
    TAX_RATES_PATH: Path = Path("configs/rules/tax_rates.yaml")
    THRESHOLDS_PATH: Path = Path("configs/rules/thresholds.yaml")
    XSD_SCHEMA_PATH: Path = Path("configs/schemas/einvoice_v1_schema.xsd")

    # Routing Thresholds
    CONFIDENCE_THRESHOLD_AUTO_APPROVE: float = 0.92
    CONFIDENCE_THRESHOLD_MANUAL_REVIEW: float = 0.75
    ARITHMETIC_TOLERANCE_VND: float = 1.0


settings = Settings()
