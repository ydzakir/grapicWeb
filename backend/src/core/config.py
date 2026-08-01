import secrets
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
    DATABASE_URL: str | None = None
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "monitoring_admin"
    POSTGRES_PASSWORD: str = "<GANTI_SAYA>"
    POSTGRES_DB: str = "monitoring_db"

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Auth & Security
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@infra.com"
    BOOTSTRAP_ADMIN_PASSWORD: str = "AdminSecurePass123!"

    _ephemeral_key: str | None = None

    def _require_secure_secret(self) -> str:
        """Refuse to run in production without an explicitly configured secret."""
        if not self.SECRET_KEY or "change_this" in self.SECRET_KEY or "<GANTI_SAYA>" in self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise RuntimeError(
                    "SECRET_KEY must be set to a strong random value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(64))\""
                )
            if not self._ephemeral_key:
                self._ephemeral_key = secrets.token_hex(64)
            return self._ephemeral_key
        return self.SECRET_KEY

    @property
    def jwt_secret_key(self) -> str:
        return self._require_secure_secret()

    # External Services
    PROMETHEUS_URL: str = "http://prometheus:9090"
    THANOS_QUERIER_URL: str = "http://thanos-querier:10902"

    # High Availability & PgBouncer Settings
    HA_MODE_ENABLED: bool = False
    PGBOUNCER_HOST: str = "pgbouncer"
    PGBOUNCER_PORT: int = 6432
    PGBOUNCER_USER: str = "monitoring_admin"
    PGBOUNCER_PASSWORD: str = "<GANTI_SAYA>"
    PGBOUNCER_DB: str = "monitoring_db"

    @property
    def pgbouncer_async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.PGBOUNCER_USER}:{self.PGBOUNCER_PASSWORD}@{self.PGBOUNCER_HOST}:{self.PGBOUNCER_PORT}/{self.PGBOUNCER_DB}"

    @property
    def effective_prometheus_url(self) -> str:
        if self.HA_MODE_ENABLED:
            return self.THANOS_QUERIER_URL
        return self.PROMETHEUS_URL

    # Collector Intervals
    STATUS_POLL_INTERVAL_SECONDS: int = 60
    INVENTORY_SCAN_INTERVAL_SECONDS: int = 300
    METRICS_COLLECT_INTERVAL_SECONDS: int = 60
    COLLECTOR_TIMEOUT_SECONDS: int = 10

    # Notification & Alerting Settings
    NOTIFICATION_PROVIDER: str = "log"
    ALERT_WEBHOOK_URL: str = ""
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 25
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "noreply@monitoring.infra"
    SMTP_TO: str = "admin@infra.com"


settings = Settings()

