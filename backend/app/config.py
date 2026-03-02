"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    database_url: str = "postgresql://jobmap:jobmap@localhost:5432/jobmap"
    geocoder_provider: str = "nominatim"
    geocoder_api_key: str = ""
    admin_api_key: str = "dev-admin-key"
    cors_origins: str = "http://localhost:3000"
    scheduler_enabled: bool = True
    scheduler_hour: int = 6  # UTC hour for daily ingestion (6 AM UTC)

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
