from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PharmaVerse AI"
    app_version: str = "0.1.0"
    debug: bool = True

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/pharmaverse"
    )

    jwt_secret: str = "CHANGE_THIS_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173"

    fabric_enabled: bool = False
    fabric_gateway_url: str = ""
    fabric_gateway_secret: str = ""
    fabric_gateway_timeout: float = 5.0

    pharmaverse_ml_artifact: str | None = None

    # ------------------------------------------------------------------ #
    # Live FDA / openFDA configuration                                     #
    # ------------------------------------------------------------------ #
    # Timeout in seconds for each outbound openFDA HTTP request.
    # Keep this low: a slow FDA response must not block the FastAPI worker.
    fda_api_timeout_seconds: float = 8.0

    # How long (seconds) to keep a cached FDA response before re-fetching.
    # openFDA NDC and Drug Shortages are updated daily; enforcement weekly.
    # A conservative default of 3 600 s (1 hour) avoids hammering FDA while
    # still reflecting the same-day update cadence for the daily sources.
    fda_cache_ttl_seconds: float = 3600.0

    # ------------------------------------------------------------------ #
    # Gmail SMTP configuration for authentication email                   #
    # ------------------------------------------------------------------ #
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "PharmaVerse AI Security"
    smtp_tls: bool = True

    # ------------------------------------------------------------------ #
    # Google OAuth configuration                                         #
    # ------------------------------------------------------------------ #
    google_client_id: str = ""
    google_client_secret: str = ""
    frontend_base_url: str = "http://localhost:5173"

    # ------------------------------------------------------------------ #
    # OTP Security Parameters                                            #
    # ------------------------------------------------------------------ #
    otp_ttl_minutes: int = 10
    otp_cooldown_seconds: int = 60
    otp_max_attempts: int = 5
    auth_link_ttl_minutes: int = 30

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> str:
        if not isinstance(value, str):
            return str(value)
        url = value.strip()
        # Render / Heroku inject 'postgres://', which SQLAlchemy 2.0 rejects
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        # psycopg2 is not installed in requirements.txt (psycopg v3 is installed)
        if url.startswith("postgresql+psycopg2://"):
            return "postgresql+psycopg://" + url[len("postgresql+psycopg2://"):]
        # Standard 'postgresql://' defaults to psycopg2 in SQLAlchemy; route to psycopg (v3)
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @field_validator("debug", mode="before")
    @classmethod
    def _parse_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "1", "yes", "on", "t", "dev", "development"):
                return True
            if normalized in ("false", "0", "no", "off", "f", "release", "prod", "production"):
                return False
        return bool(value)

    @model_validator(mode="after")
    def _validate_production_configuration(self) -> "Settings":
        # Strict configuration validation only applies in production mode
        if not self.debug:
            raw_db = self.database_url.lower().strip()
            if (
                not raw_db
                or "localhost" in raw_db
                or "127.0.0.1" in raw_db
                or "::1" in raw_db
            ):
                raise ValueError(
                    "Production safety violation: DATABASE_URL must be explicitly configured "
                    "with a remote database host. Default localhost database is forbidden when DEBUG=false."
                )

            raw_secret = self.jwt_secret.strip()
            if (
                not raw_secret
                or raw_secret in ("CHANGE_THIS_SECRET", "secret", "changeme", "default")
                or len(raw_secret) < 32
            ):
                raise ValueError(
                    "Production safety violation: JWT_SECRET must be explicitly configured "
                    "with a cryptographically secure key of at least 32 characters when DEBUG=false."
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()