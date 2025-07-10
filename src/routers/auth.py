from fastapi import APIRouter, HTTPException, Request, Depends  # Added Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import logging
import os
from ..config import get_settings
from ..models.user import User, UserRead # UserRead is here
from ..utils.auth import create_access_token, get_current_user
from ..database import SessionLocal, get_db # Add get_db
from sqlalchemy.orm import Session # Add Session
import json
from datetime import timedelta # Keep timedelta
from jose import jwt # Keep jose jwt
# Removed duplicated imports below

# Configure logging
# logging.basicConfig(level=logging.DEBUG) # This will be handled by main app or uvicorn
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize settings for GitHub OAuth
settings = get_settings()
# Removed direct os.environ.get for GITHUB_CLIENT_ID and related logging,
# as settings.github_client_id is the consolidated way to access it.
logger.debug(f"Settings GITHUB_CLIENT_ID loaded: {bool(settings.github_client_id)}")


@router.get("/login", name="auth_login")  # Path changed from /auth/login
async def login():
    """Step 1: Initiate GitHub OAuth Flow
    Redirects user to GitHub's authorization page"""
    logger.info(f"Starting OAuth flow with client ID: {settings.github_client_id[:4]}...")
    
    # Construct GitHub OAuth URL with required parameters
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_callback_url}"
        "&scope=read:org,repo,user:email"  # Added user:email scope
    )
    return RedirectResponse(url=github_auth_url)

# Update callback function
@router.get("/callback")  # Path changed from /auth/callback
async def callback(request: Request, code: str | None = None, db: Session = Depends(get_db)): # Added db dependency
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")

    try:
        # Exchange code for token
        token_url = "https://github.com/login/oauth/access_token"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code
                },
                headers={"Accept": "application/json"}
            )
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="Failed to get access token")

            # Fetch user data
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            user_data = user_response.json()

            # Get user's email
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            emails = email_response.json()
            primary_email = next((email["email"] for email in emails if email["primary"]), None)

            # Database operations using injected db session
            user = db.query(User).filter(User.github_id == str(user_data["id"])).first()
            if not user:
                user = User(
                    github_id=str(user_data["id"]),
                    username=user_data["login"],
                    email=primary_email,
                    access_token=access_token
                )
                db.add(user)
            else:
                user.access_token = access_token
                user.email = primary_email
            db.commit()
            db.refresh(user)

            # Create JWT token for our session
            app_jwt_token = create_access_token(
                data={"sub": user.username, "github_id": user.github_id}, # Include github_id or other stable user id
                expires_delta=timedelta(days=1)
            )

            frontend_url = "http://localhost:3000/"
            redirect_response = RedirectResponse(url=frontend_url, status_code=302)

            # Set JWT token for app session
            redirect_response.set_cookie(
                key="jwt_token",
                value=app_jwt_token,
                httponly=True,
                max_age=86400,  # 24 hours
                secure=False, # Set to True in production if using HTTPS
                samesite="lax",
                path="/"
            )
            # Also store the GitHub access token if frontend needs to make direct GitHub API calls (consider security implications)
            # For now, let's assume the backend proxies all GitHub requests or the frontend doesn't need it directly.
            # If it is needed, ensure it's handled securely.
            # For this iteration, we will also set the github_token as a cookie.
            redirect_response.set_cookie(
                key="github_token",
                value=user.access_token, # This is the GitHub OAuth token
                httponly=True,
                max_age=86400, # 24 hours
                secure=False, # Set to True in production
                samesite="lax",
                path="/"
            )
            return redirect_response
            # No db.close() needed here, Depends(get_db) handles it.
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        # It's good practice to rollback in case of error during db operations,
        # though Depends(get_db) doesn't do this automatically.
        # For now, simple error raising. Consider adding rollback if complex transactions.
        db.rollback() # Add rollback on exception
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/token")  # Path changed from /auth/debug/token
async def debug_token(current_user: User = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {current_user.access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        scopes_response = await client.get(
            "https://api.github.com/user/orgs",
            headers={
                "Authorization": f"token {current_user.access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        return {
            "status": response.status_code,
            "scopes": response.headers.get("X-OAuth-Scopes"),
            "user_data": response.json(),
            "orgs_status": scopes_response.status_code,
            "orgs_response": scopes_response.json() if scopes_response.status_code == 200 else None
        }

@router.get("/verify", response_model=UserRead) # Use UserRead as response_model
async def verify_auth(current_user: User = Depends(get_current_user)):
    """
    Verify if the user is authenticated based on the jwt_token cookie.
    Returns basic user information if authenticated.
    """
    # current_user is an SQLAlchemy User model instance.
    # FastAPI will automatically convert it to UserRead schema due to response_model.
    # However, the frontend expects a dict: {"message": "...", "user": UserRead_dict}
    # So, we'll construct this dictionary. UserRead.from_orm(current_user) can be used.

    user_data = UserRead.from_orm(current_user)
    return JSONResponse(status_code=200, content={
        "message": "User is authenticated",
        "user": user_data.model_dump() # Use .model_dump() for Pydantic v2
    })