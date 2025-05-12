from fastapi import APIRouter, HTTPException, Request, Depends  # Added Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import logging
import os
from ..config import get_settings
from ..models.user import User
from ..utils.auth import create_access_token, get_current_user
from ..database import SessionLocal
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
import httpx
import logging
import os
from ..config import get_settings
from ..models.user import User
from ..utils.auth import create_access_token, get_current_user
from ..database import SessionLocal
from datetime import timedelta
from jose import jwt

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

# # Add to imports
# from fastapi.middleware.cors import CORSMiddleware



# Update callback function
@router.get("/auth/callback")
async def callback(request: Request, code: str | None = None):
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

            # Database operations
            db = SessionLocal()
            try:
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

                # Create JWT token
                jwt_token = create_access_token(
                    data={"sub": user.username},
                    expires_delta=timedelta(days=1)
                )

                # Prepare response data
                response_data = {
                    "access_token": jwt_token,
                    "token_type": "bearer",
                    "github_token": user.access_token,
                    "user": {
                        "username": user.username,
                        "email": user.email
                    }
                }

                # Return redirect response
                frontend_url = "http://localhost:3000"
                return RedirectResponse(
                    url=f"{frontend_url}?auth_data={json.dumps(response_data)}",
                    status_code=302
                )
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/debug/token")
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

@router.get("/auth/verify")
async def verify_auth(request: Request):
    """Verify if the user is authenticated by checking the access token"""
    try:
        # Check if the user is authenticated
       
       token = request.cookies.get("jwt_token")

       if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

       current_user = await get_current_user(token)
      
       print(f"Current user:", {"current_user": current_user.username})
       
       if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
       # If authenticated, return user data
       return JSONResponse(status_code=200, content={
            "message": "User is authenticated",
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "access_token": current_user.access_token
            }
        })
    except Exception as e:
        logger.error(f"Error in verify_auth: {e}")
        print(f"Error in verify_auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))