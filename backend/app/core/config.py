from pydantic import Field
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

    # Security - all required, no defaults
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    BCRYPT_ROUNDS: int

    # Runtime - required
    ENVIRONMENT: str
    LOG_LEVEL: str
    BACKEND_CORS_ORIGINS: list[str]

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
