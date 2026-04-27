"""
全局配置
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "MedIntel Cloud"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://medintel:medintel@localhost:5432/medintel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MIMO
    mimo_api_key: str = ""
    mimo_base_url: str = "https://api.xiaomimimo.com/v1"

    # Auth
    secret_key: str = "change-me-in-production"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
