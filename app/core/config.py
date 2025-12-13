from functools import lru_cache
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "ksuns"
    frontend_url: str = "http://localhost:3000"

    # Database
    db_user: str = ""
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "ksuns_db"
    ssl_ca_path: Optional[str] = None

    # JWT
    jwt_secret: str = ""
    access_token_ttl_min: int = 15
    refresh_token_ttl_day: int = 14

    # Refresh Cookie
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = True
    refresh_cookie_samesite: str = "none"
    refresh_cookie_path: str = "/"
    refresh_cookie_domain: Optional[str] = None

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Azure OpenAI (Legacy)
    target_uri: str = ""
    ai_foundary_key: str = ""

    # Azure OpenAI (New)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"

    # CORS (accepts comma-separated string or list)
    cors_origins: Union[str, List[str]] = ""

    # Azure deployment
    scm_do_build_during_deployment: Optional[str] = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if not v:
                return []
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
