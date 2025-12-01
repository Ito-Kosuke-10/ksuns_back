from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # back/
# 明示的に back/.env を読む（実行ディレクトリに依存しない）
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    app_name: str = Field("ksuns", validation_alias="APP_NAME")

    db_user: str = Field(..., validation_alias="DB_USER")
    db_password: str = Field(..., validation_alias="DB_PASSWORD")
    db_host: str = Field(..., validation_alias="DB_HOST")
    db_port: int = Field(3306, validation_alias="DB_PORT")
    db_name: str = Field(..., validation_alias="DB_NAME")
    ssl_ca_path: Optional[str] = Field(None, validation_alias="SSL_CA_PATH")

    cors_origins: List[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")

    jwt_secret: str = Field(..., validation_alias="JWT_SECRET")
    access_token_ttl_min: int = Field(15, validation_alias="ACCESS_TOKEN_TTL_MIN")
    refresh_token_ttl_day: int = Field(14, validation_alias="REFRESH_TOKEN_TTL_DAY")
    refresh_cookie_name: str = Field("ksuns_refresh_token", validation_alias="REFRESH_COOKIE_NAME")
    refresh_cookie_secure: bool = Field(True, validation_alias="REFRESH_COOKIE_SECURE")
    refresh_cookie_path: str = Field("/", validation_alias="REFRESH_COOKIE_PATH")
    refresh_cookie_samesite: str = Field("lax", validation_alias="REFRESH_COOKIE_SAMESITE")
    refresh_cookie_domain: Optional[str] = Field(None, validation_alias="REFRESH_COOKIE_DOMAIN")
    access_token_storage: str = Field("memory", validation_alias="ACCESS_TOKEN_STORAGE")

    google_client_id: str = Field(..., validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., validation_alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., validation_alias="GOOGLE_REDIRECT_URI")

    target_uri: str = Field(..., validation_alias="TARGET_URI")
    ai_foundry_key: str = Field(..., validation_alias="AI_FOUNDARY_KEY")
    frontend_url: str = Field("http://localhost:3000", validation_alias="FRONTEND_URL")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [origin for origin in value.split(",") if origin]
        return []

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        host = self.db_host
        port = self.db_port
        name = self.db_name
        ssl_suffix = ""
        if self.ssl_ca_path:
            ssl_suffix = f"?ssl_ca={quote_plus(self.ssl_ca_path)}"
        return f"mysql+asyncmy://{user}:{password}@{host}:{port}/{name}{ssl_suffix}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns cached Settings instance. Use this helper instead of instantiating Settings directly.
    """
    return Settings()  # type: ignore[arg-type]
