from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    postgres_url: str = "postgresql+asyncpg://arcshield:arcshield@localhost:5432/arcshield"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    embedding_model: str = "all-MiniLM-L6-v2"
    media_root: str = "/data/media/frames"
    api_key: str = "changeme"


@lru_cache
def get_settings() -> Settings:
    return Settings()
