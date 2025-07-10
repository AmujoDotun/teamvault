# import asyncio # Unused
from fastapi import FastAPI, Request
# import urllib.parse # Unused
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
# import json # Unused
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Update CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],  # Add both URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the current directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

# Set up templates directory
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

# Mount static files with absolute path
app.mount("/static", 
          StaticFiles(directory=os.path.join(current_dir, "static")), 
          name="static")

# Comments updated:
# The main "/" route handles checking for session cookies and redirecting to login
# or fetching user data to render the dashboard.
# The frontend /auth/callback endpoint was removed as the backend now handles
# the GitHub OAuth callback directly, sets cookies, and redirects to this frontend's "/" path.

@app.get("/")
async def home(request: Request):
    jwt_token = request.cookies.get("jwt_token")
    # github_token is also set as an http-only cookie by the backend.
    # The frontend / route will rely on jwt_token for checking auth status.
    # If specific GitHub API calls are needed from frontend, it would be through backend proxy anwyay.
    
    if not jwt_token: # Only need to check jwt_token now for initial auth check
        print("No JWT token found, redirecting to login")
        # Redirect to backend's login initiation URL
        return RedirectResponse(url="http://localhost:8000/api/v1/auth/login") # Updated URL
    
    try:
        # The frontend doesn't need to pass X-Github-Token if the backend's /api/auth/verify
        # can verify the user solely based on the jwt_token (which should contain user identity).
        # The current /api/auth/verify in src/routers/auth.py uses get_current_user(token) which is good.
        async with httpx.AsyncClient() as client:
            verify_response = await client.get(
                "http://localhost:8000/api/v1/auth/verify", # Updated URL
                cookies={"jwt_token": jwt_token}, # Pass the jwt_token cookie
                timeout=30.0
            )
            
            if verify_response.status_code == 200:
                user_data = verify_response.json()
                # The user_data from /api/auth/verify contains user details.
                return templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "title": "GitHub Organization Manager",
                    "user": user_data.get("user") # user_data itself is {"message": ..., "user": {...}}
                })
            
            print(f"Token verification failed: {verify_response.status_code} - {verify_response.text}")
            # If verification fails, clear cookies and redirect to login
            redirect_response = RedirectResponse(url="http://localhost:8000/api/auth/login")
            redirect_response.delete_cookie("jwt_token")
            redirect_response.delete_cookie("github_token") # Also clear github_token if it was set
            return redirect_response
            
    except Exception as e:
        print(f"Error verifying session: {e}")
        # In case of any other error, clear cookies and redirect to login
        redirect_response = RedirectResponse(url="http://localhost:8000/api/auth/login")
        redirect_response.delete_cookie("jwt_token")
        redirect_response.delete_cookie("github_token")
        return redirect_response

# Removed the /auth/callback endpoint from frontend app.

