from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .auth.routes import router as auth_router
from .config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount auth routes
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}