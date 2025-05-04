from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from .config import get_settings

settings = get_settings()

# Ensure data directory exists
data_dir = "/app/data"
os.makedirs(data_dir, exist_ok=True)

# Update database URL to use data directory
SQLALCHEMY_DATABASE_URL = "sqlite:////app/data/teamvault.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()