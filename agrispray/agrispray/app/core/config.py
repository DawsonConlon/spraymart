from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://agrispray:password@localhost:5432/agrispray"

    # Environment Canada API
    ECCC_BASE_URL: str = "https://api.weather.gc.ca"

    # John Deere Operations Center API
    JOHN_DEERE_CLIENT_ID: str = ""
    JOHN_DEERE_CLIENT_SECRET: str = ""
    JOHN_DEERE_BASE_URL: str = "https://sandboxapi.deere.com/platform"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
