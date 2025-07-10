from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from ..database import Base
from pydantic import BaseModel # Add pydantic import
from typing import Optional # For Optional fields

# Pydantic schema for User response
class UserRead(BaseModel):
    id: int
    github_id: str
    username: str
    email: Optional[str] = None # Match nullability with SQLAlchemy model
    # access_token: str # Exclude GitHub access token by default

    class Config:
        from_attributes = True # Correct attribute for Pydantic V2

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    access_token = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())