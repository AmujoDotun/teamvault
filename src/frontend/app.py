import asyncio
from fastapi import FastAPI, Request
import urllib.parse
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import json
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

@app.get("/")
async def home(request: Request, auth_data: str | None = None):
    context = {
        "request": request,
        "title": "GitHub Organization Manager",
        "auth_data": auth_data
    }
    return templates.TemplateResponse("dashboard.html", context)



@app.get("/auth/callback")
async def auth_callback(request: Request, code: str):
    try:
        # Add delay to respect rate limits
        await asyncio.sleep(2)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8000/auth/callback?code={code}",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "TeamVault-App"  # Add User-Agent to reduce rate limiting
                },
                follow_redirects=False
            )
            
            if response.status_code == 429:  # Rate limit exceeded
                return templates.TemplateResponse("error.html", {
                    "request": request,
                    "error": "GitHub rate limit exceeded. Please wait a few minutes before trying again."
                })
            
            if response.status_code == 302:
                location = response.headers.get("location", "")
                if "auth_data=" in location:
                    auth_data = location.split("auth_data=")[1]
                    data = json.loads(urllib.parse.unquote(auth_data))
                    
                    # Create redirect response
                    redirect = RedirectResponse(url="/")
                    # Set auth data as cookie
                    redirect.set_cookie(
                        key="jwt_token",
                        value=data["access_token"],
                        httponly=True,
                        max_age=86400  # 24 hours
                    )
                    redirect.set_cookie(
                        key="github_token",
                        value=data["github_token"],
                        httponly=True,
                        max_age=86400
                    )
                    return redirect
            
            raise Exception(f"Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"Error in callback: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

@app.get("/")
async def home(request: Request):
    jwt_token = request.cookies.get("jwt_token")
    github_token = request.cookies.get("github_token")
    
    if not jwt_token or not github_token:
        print("No tokens found, redirecting to login")
        return RedirectResponse(url="http://localhost:8000/auth/login")
    
    try:
        async with httpx.AsyncClient() as client:
            verify_response = await client.get(
                "http://localhost:8000/api/auth/verify",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "X-Github-Token": github_token
                },
                timeout=30.0
            )
            
            if verify_response.status_code == 200:
                user_data = verify_response.json()
                return templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "title": "GitHub Organization Manager",
                    "user": user_data
                })
            
            print(f"Token verification failed: {verify_response.status_code}")
            response = RedirectResponse(url="http://localhost:8000/auth/login")
            response.delete_cookie("jwt_token")
            response.delete_cookie("github_token")
            return response
            
    except Exception as e:
        print(f"Error verifying session: {e}")
        return RedirectResponse(url="http://localhost:8000/auth/login")

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8000/auth/callback?code={code}",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "TeamVault-App"
                },
                follow_redirects=False,
                timeout=30.0
            )
            
            if response.status_code == 302:
                location = response.headers.get("location", "")
                if "auth_data=" in location:
                    auth_data = location.split("auth_data=")[1]
                    data = json.loads(urllib.parse.unquote(auth_data))
                    
                    redirect = RedirectResponse(url="/", status_code=302)
                    for key, value in [
                        ("jwt_token", data["access_token"]),
                        ("github_token", data["github_token"])
                    ]:
                        redirect.set_cookie(
                            key=key,
                            value=value,
                            httponly=True,
                            secure=False,
                            samesite="lax",
                            max_age=86400,
                            path="/"
                        )
                    return redirect
            
            error_msg = f"Authentication failed (Status: {response.status_code})"
            print(f"Auth error: {error_msg}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": error_msg
            })
            
    except Exception as e:
        print(f"Callback error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

