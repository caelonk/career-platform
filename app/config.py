from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./career_platform.db")
    secret_key: str = Field(default="development-secret-key")
    admin_password: str = Field(default="pbkdf2_sha256$200000$Fvzz02RnT3msIEguSTqeKg==$2BYWgTJVHt0dFTiNHQ54vReZRxM4iAi4Ho6i791gvs4=")
    snapshot_dir: str = Field(default="./snapshots")
    environment: str = Field(default="development")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.environment == "production" and not self.secret_key.strip():
            raise ValueError("SECRET_KEY must be set when ENVIRONMENT=production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
