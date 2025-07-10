from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer # No longer needed
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from ..config import get_settings
from ..database import get_db # Changed from SessionLocal
from sqlalchemy.orm import Session # Import Session
from ..models.user import User
from fastapi import Request # Import Request

settings = get_settings()
# oauth2_scheme and its import OAuth2PasswordBearer are no longer needed.

# Dependency to get token from cookie
async def get_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get("jwt_token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt

async def get_current_user(token: str | None = Depends(get_token_from_cookie), db: Session = Depends(get_db)): # Added db dependency
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}, # This header might change if not using Bearer scheme
    )
    if token is None: # Handle case where cookie is not found
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Use the injected db session
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
    # No db.close() or try/finally needed here for db session management