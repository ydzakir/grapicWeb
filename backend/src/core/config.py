from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "Infrastructure Monitoring & Auto-Topology"
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: str = "INFO"

    # Database Settings
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "monitoring_admin"
    POSTGRES_PASSWORD: str = "change_this_in_production_secure_pass_123"
    POSTGRES_DB: str = "monitoring_db"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Auth & Security
    SECRET_KEY: str = "change_this_to_a_secure_random_64_char_string_for_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@infra.com"
    BOOTSTRAP_ADMIN_PASSWORD: str = "AdminSecurePass123!"

    # External Services
    PROMETHEUS_URL: str = "http://prometheus:9090"

    # Collector Intervals
    STATUS_POLL_INTERVAL_SECONDS: int = 60
    INVENTORY_SCAN_INTERVAL_SECONDS: int = 300
    METRICS_COLLECT_INTERVAL_SECONDS: int = 60
    COLLECTOR_TIMEOUT_SECONDS: int = 10


settings = Settings()
