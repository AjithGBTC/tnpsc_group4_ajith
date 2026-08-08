from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # CORS_ORIGINS is intentionally comma-separated in Render and Docker envs,
    # rather than JSON (the pydantic-settings default for list fields).
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore", enable_decoding=False)
    app_env: str = "development"
    debug: bool = False
    # Safe development defaults make operational endpoints and the test suite
    # importable. Deployment must replace every value through environment vars.
    database_url: str = "postgresql+asyncpg://exam_admin:exam_admin@localhost:5432/exam_platform"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "change-this-development-secret-before-deployment"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    cors_origins: list[str] = []
    s3_bucket: str = ""
    aws_region: str = "ap-south-1"
    firebase_credentials_path: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    otp_ttl_minutes: int = 5
    otp_max_attempts: int = 5
    request_rate_limit_per_minute: int = 120
    otp_rate_limit_per_hour: int = 5

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()] if isinstance(value, str) else value

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: bool | str) -> bool:
        # Accept legacy deployment values such as "release" as false.
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "debug"}
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def async_database_url(cls, value: str) -> str:
        # Render supplies postgresql://, while SQLAlchemy's async engine needs asyncpg.
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
