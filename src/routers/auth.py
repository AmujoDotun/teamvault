from fastapi import APIRouter, HTTPException, Request, Depends  # Added Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import logging
import os
from ..config import get_settings
from ..models.user import User
from ..utils.auth import create_access_token, get_current_user
from ..database import SessionLocal
from datetime import timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize settings and environment variables for GitHub OAuth
settings = get_settings()
client_id = os.environ.get('GITHUB_CLIENT_ID', 'not_set')
logger.debug(f"Direct env GITHUB_CLIENT_ID: {client_id}")
logger.debug(f"Settings GITHUB_CLIENT_ID: {settings.github_client_id}")

@router.get("/auth/login", name="auth_login")
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

@router.get("/auth/callback")
async def callback(request: Request, code: str | None = None):
    """Step 2: Handle GitHub OAuth Callback
    Exchanges authorization code for access token and creates user session"""
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")

    # Step 2a: Exchange authorization code for access token
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

        # Step 2b: Fetch user information from GitHub API
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        user_data = user_response.json()

        # Get user's email from GitHub API
        email_response = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        emails = email_response.json()
        primary_email = next((email["email"] for email in emails if email["primary"]), None)

        # Create or update user in database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.github_id == str(user_data["id"])).first()
            if not user:
                user = User(
                    github_id=str(user_data["id"]),
                    username=user_data["login"],
                    email=primary_email,  # Use primary email
                    access_token=access_token
                )
                db.add(user)
            else:
                user.access_token = access_token
                user.email = primary_email  # Update email if changed
            db.commit()
            db.refresh(user)

            # Step 2d: Create JWT session token for our application
            access_token = create_access_token(
                data={"sub": user.username},
                expires_delta=timedelta(days=1)
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "username": user.username,
                    "email": user.email
                }
            }
        finally:
            db.close()

@router.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Protected endpoint: Returns authenticated user's information
    Uses JWT token for authentication"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "github_id": current_user.github_id
    }