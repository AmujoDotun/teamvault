from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .config import get_settings

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TeamVault",
    description="GitHub Organization Management API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to TeamVault"}