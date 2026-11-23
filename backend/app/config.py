"""Central configuration. Every secret is read from environment variables
(.env file in development). Nothing sensitive is hard-coded in the source."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    jwt_secret: str = "dev-only-secret-change-me-dev-only-secret"
    jwt_expire_minutes: int = 720
    trust_proxy: bool = False

    database_url: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket: str = "portfolio"

    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    allowed_email_domains: str = ""

    captcha_enabled: bool = True
    recaptcha_secret_key: str = ""

    paymongo_secret_key: str = ""
    paymongo_webhook_secret: str = ""
    platform_fee_percent: float = 10.0

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Student Gig Marketplace"

    @property
    def allowed_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
