import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Change data directory to user's home directory
data_dir = os.path.expanduser('~/github-user-management-data')
os.makedirs(data_dir, exist_ok=True)

# Database URL
DATABASE_URL = f"sqlite:///{os.path.join(data_dir, 'app.db')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()