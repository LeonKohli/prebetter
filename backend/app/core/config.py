from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
import secrets

class Settings(BaseSettings):
    PROJECT_NAME: str = "Prebetter Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # MySQL settings for Prelude (read-only)
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: str = "3306"
    MYSQL_PRELUDE_DB: str = "prelude"
    
    # MySQL settings for Prebetter (user management)
    MYSQL_PREBETTER_DB: str = "prebetter"
    
    # JWT settings
    JWT_SECRET_KEY: str = "your-secret-key"  # Change this in production!
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Security settings
    SECRET_KEY: str = secrets.token_urlsafe(32)  # Generate a secure random key if not provided
    ALGORITHM: str = "HS256"
    
    # Computed DATABASE_URLs
    @property
    def PRELUDE_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_PRELUDE_DB}"
    
    @property
    def PREBETTER_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_PREBETTER_DB}"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()