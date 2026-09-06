"""Central application settings. Production defaults fail closed."""
import json
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AI_API_KEY: str
    AI_API_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"
    AI_PROVIDER: str = "openai"
    DAILY_AI_REQUEST_LIMIT: int = 20
    MAX_AI_OUTPUT_TOKENS: int = 1200

    FRONTEND_URL: str = "http://localhost:5173"
    INITIAL_ADMIN_EMAIL: str | None = None

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_USE_TLS: bool = True

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15
    TOTP_ISSUER_NAME: str = "AI Backend"

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    TRUSTED_PROXY_NETWORKS: list[str] = [
        "127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
    ]

    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    MAX_FILES_PER_USER: int = 100
    MAX_STORAGE_PER_USER_MB: int = 500

    PAYMENT_PROVIDER: str = "stripe"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""
    PAYPAL_API_BASE: str = "https://api-m.sandbox.paypal.com"
    BILLING_SUCCESS_PATH: str = "/billing/success"
    BILLING_CANCEL_PATH: str = "/billing/cancel"

    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    CACHE_TTL_SECONDS: int = 60

    # Healthcare public sources / integrations. Credentials must be supplied separately.
    CLINICALTRIALS_BASE_URL: str = "https://clinicaltrials.gov/api/v2"
    RXNORM_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    PUBMED_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    OPENFDA_BASE_URL: str = "https://api.fda.gov"
    NPI_REGISTRY_BASE_URL: str = "https://npiregistry.cms.hhs.gov/api"
    MEDICARE_CARE_COMPARE_BASE_URL: str = "https://data.cms.gov"
    DAILYMED_BASE_URL: str = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
    CMS_OPEN_DATA_BASE_URL: str = "https://data.cms.gov/provider-data/api/1"
    CMS_COVERAGE_BASE_URL: str = "https://api.coverage.cms.gov"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production(self):
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY.startswith("change_me"):
                raise ValueError("A strong JWT_SECRET_KEY is required in production")
            if not self.AI_API_KEY or self.AI_API_KEY.startswith("your_"):
                raise ValueError("A real AI_API_KEY is required in production")
            if not self.INITIAL_ADMIN_EMAIL:
                raise ValueError("INITIAL_ADMIN_EMAIL is required in production")
            if not self.SMTP_HOST or not self.SMTP_FROM_EMAIL:
                raise ValueError("SMTP must be configured in production")
            if any("localhost" in origin or "127.0.0.1" in origin for origin in self.CORS_ORIGINS):
                raise ValueError("Production CORS_ORIGINS cannot contain localhost")
        return self


settings = Settings()
