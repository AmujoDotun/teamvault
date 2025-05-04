from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, init_db
from .routers import auth
from .config import get_settings

# Initialize database tables
init_db()

app = FastAPI(
    title="TeamVault",
    description="GitHub Organization Management API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the auth router
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Welcome to TeamVault"}

@app.get("/routes")
async def list_routes():
    """Debug endpoint to list all available routes"""
    routes = []
    for route in app.routes:
        routes.append(f"{route.methods} {route.path}")
    return {"available_routes": routes}

@app.get("/debug/env")
async def debug_env():
    settings = get_settings()
    return {
        "callback_url": settings.github_callback_url,
        "client_id_length": len(settings.github_client_id) if settings.github_client_id else 0
    }

@app.get("/auth/test")
async def test_auth():
    settings = get_settings()
    return {
        "message": "Auth route working",
        "client_id": settings.github_client_id[:4] + "..." if settings.github_client_id else None,
        "callback_url": settings.github_callback_url
    }