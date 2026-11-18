from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    geoapify_api_key: str = ''
    database_url: str = ''
    database_url_unpooled: str = ''
    model_config = SettingsConfigDict(env_file=(ROOT / '.env', ROOT / '.env.local'), extra='ignore')

@lru_cache
def get_settings():
    return Settings()
