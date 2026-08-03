from functools import lru_cache
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")
    app_env: str = "development"
    debug: bool = False
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    cors_origins: list[str] = []
    s3_bucket: str = ""
    aws_region: str = "ap-south-1"
    firebase_credentials_path: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        return value.split(",") if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
