from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # App metadata (internal, not deployment config)
    PROJECT_NAME: str = "Prebetter Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database - all required, no defaults (12-factor)
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str
    MYSQL_PORT: str
    MYSQL_PRELUDE_DB: str
    MYSQL_PREBETTER_DB: str

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

    @property
    def PRELUDE_DATABASE_URL(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=int(self.MYSQL_PORT),
            database=self.MYSQL_PRELUDE_DB,
        )

    @property
    def PREBETTER_DATABASE_URL(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=int(self.MYSQL_PORT),
            database=self.MYSQL_PREBETTER_DB,
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
