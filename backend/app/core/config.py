from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "Prebetter Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: str = "3306"
    MYSQL_PRELUDE_DB: str = "prelude"

    MYSQL_PREBETTER_DB: str = "prebetter"

    # JWT / Auth
    SECRET_KEY: str  # Required. Set in environment/.env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BCRYPT_ROUNDS: int = 14

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    @property
    def PRELUDE_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_PRELUDE_DB}"

    @property
    def PREBETTER_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_PREBETTER_DB}"

    # CORS: keep restrictive by default; override in .env
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
