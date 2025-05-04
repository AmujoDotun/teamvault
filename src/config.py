from pydantic_settings import BaseSettings
from functools import lru_cache
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get absolute path to project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
ENV_FILE = PROJECT_ROOT / '.env'

# Verify .env file exists and load it
if not ENV_FILE.exists():
    raise FileNotFoundError(f".env file not found at {ENV_FILE}")

logger.info(f"Loading environment from: {ENV_FILE}")
with open(ENV_FILE) as f:
    logger.info(f"Environment file contents available: {f.readable()}")

class Settings(BaseSettings):
    github_client_id: str
    github_client_secret: str
    github_callback_url: str
    database_url: str
    secret_key: str

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = 'utf-8'
        case_sensitive = False

    @property
    def is_valid(self) -> bool:
        return (
            self.github_client_id and 
            self.github_client_id != "your_client_id_here" and
            len(self.github_client_id) > 10
        )

@lru_cache()
def get_settings() -> Settings:
    try:
        settings = Settings()
        
        # Validate settings
        if not settings.is_valid:
            logger.error(f"Current working directory: {os.getcwd()}")
            logger.error(f"Project root: {PROJECT_ROOT}")
            logger.error(f"Environment file path: {ENV_FILE}")
            logger.error(f"Environment file exists: {ENV_FILE.exists()}")
            logger.error(f"Current settings values:")
            logger.error(f"  GITHUB_CLIENT_ID: {settings.github_client_id}")
            logger.error(f"  CALLBACK_URL: {settings.github_callback_url}")
            raise ValueError(
                "Invalid GitHub Client ID. Please ensure your .env file contains valid credentials."
            )
            
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        logger.error(f"Environment variables: {dict(os.environ)}")
        raise