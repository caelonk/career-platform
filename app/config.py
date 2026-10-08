from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_POSTGRES_PREFIXES = ("postgres://", "postgresql://")

DEFAULT_SECRET_KEYS = frozenset({"development-secret-key", "change-me-in-development", "change-me"})
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2_sha256$200000$Fvzz02RnT3msIEguSTqeKg==$2BYWgTJVHt0dFTiNHQ54vReZRxM4iAi4Ho6i791gvs4="


def normalize_database_url(url: str) -> str:
    """Point Postgres URLs at the psycopg 3 driver; Railway hands out bare postgresql:// URLs."""
    for prefix in _POSTGRES_PREFIXES:
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./career_platform.db")
    secret_key: str = Field(default="development-secret-key")
    admin_password: str = Field(default=DEFAULT_ADMIN_PASSWORD_HASH)
    snapshot_dir: str = Field(default="./snapshots")
    environment: str = Field(default="development")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url_field(cls, value: str) -> str:
        return normalize_database_url(value)

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.environment != "production":
            return self
        if not self.secret_key.strip() or self.secret_key in DEFAULT_SECRET_KEYS:
            raise ValueError("SECRET_KEY must be set to a private value when ENVIRONMENT=production.")
        if self.admin_password == DEFAULT_ADMIN_PASSWORD_HASH:
            raise ValueError("ADMIN_PASSWORD must be set to your own password hash when ENVIRONMENT=production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
