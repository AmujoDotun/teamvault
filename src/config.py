from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    github_client_id: str
    github_client_secret: str
    github_callback_url: str
    database_url: str
    secret_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()