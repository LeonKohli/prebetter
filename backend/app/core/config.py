from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App metadata (internal, not deployment config)
    PROJECT_NAME: str = "Prebetter Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # OpenSearch. Without a user the client connects unauthenticated.
    OPENSEARCH_URL: str
    OPENSEARCH_INDEX: str
    OPENSEARCH_REQUEST_INDEX: str
    OPENSEARCH_USER: str | None = None
    OPENSEARCH_PASSWORD: str | None = None

    # Auth - tokens are issued by Better Auth (Nuxt) and verified here via JWKS.
    # BETTER_AUTH_URL is the Better Auth base URL; it is the JWT issuer/audience.
    BETTER_AUTH_URL: str
    JWT_ALGORITHM: str = "EdDSA"

    # Runtime - required
    ENVIRONMENT: str
    LOG_LEVEL: str
    BACKEND_CORS_ORIGINS: list[str]

    @property
    def JWKS_URL(self) -> str:
        return f"{self.BETTER_AUTH_URL.rstrip('/')}/api/auth/jwks"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
