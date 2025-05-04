from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import logging
import os
from ..config import get_settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# Get settings and log values for debugging
settings = get_settings()
client_id = os.environ.get('GITHUB_CLIENT_ID', 'not_set')
logger.debug(f"Direct env GITHUB_CLIENT_ID: {client_id}")
logger.debug(f"Settings GITHUB_CLIENT_ID: {settings.github_client_id}")

@router.get("/auth/test")
async def test_auth():
    """Test endpoint to verify environment variables"""
    direct_client_id = os.environ.get('GITHUB_CLIENT_ID', 'not_set')
    return {
        "message": "Auth route working",
        "client_id": direct_client_id[:4] + "..." if direct_client_id != 'not_set' else 'not_set',
        "settings_client_id": settings.github_client_id[:4] + "..." if settings.github_client_id else 'not_set',
        "callback_url": settings.github_callback_url,
        "env_vars_present": {
            "GITHUB_CLIENT_ID": "GITHUB_CLIENT_ID" in os.environ,
            "GITHUB_CLIENT_SECRET": "GITHUB_CLIENT_SECRET" in os.environ,
            "GITHUB_CALLBACK_URL": "GITHUB_CALLBACK_URL" in os.environ
        }
    }

@router.get("/auth/login", name="auth_login")
async def login():
    """Redirect to GitHub OAuth login"""
    logger.info(f"Starting OAuth flow with client ID: {settings.github_client_id[:4]}...")
    
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_callback_url}"
        "&scope=read:org,repo"
    )
    logger.info(f"Generated auth URL: {github_auth_url}")
    return RedirectResponse(url=github_auth_url)

@router.get("/auth/callback")
async def callback(request: Request, code: str | None = None):
    """Handle GitHub OAuth callback"""
    logger.info("Received callback request")
    logger.info(f"Callback received with code: {code[:5] if code else 'None'}...")
    if not code:
        raise HTTPException(
            status_code=400,
            detail="No authorization code provided. Please start the OAuth flow from /login"
        )

    # Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_callback_url
            },
            headers={"Accept": "application/json"}
        )
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise HTTPException(
                status_code=400,
                detail="Failed to exchange code for access token"
            )

        token_data = response.json()
        
        if "error" in token_data:
            logger.error(f"GitHub error: {token_data['error']}")
            raise HTTPException(
                status_code=400,
                detail=token_data.get("error_description", "Authentication failed")
            )

        # Get user information
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token_data['access_token']}",
                "Accept": "application/json"
            }
        )
        user_data = user_response.json()

    return JSONResponse({
        "message": "Successfully authenticated",
        "user": {
            "login": user_data.get("login"),
            "name": user_data.get("name"),
            "avatar_url": user_data.get("avatar_url")
        }
    })