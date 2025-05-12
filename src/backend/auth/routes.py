from fastapi import APIRouter, HTTPException, Header
from jose import jwt, JWTError
import httpx
from ..config import JWT_SECRET_KEY, JWT_ALGORITHM

router = APIRouter()

@router.get("/verify")
async def verify_session(
    authorization: str = Header(None),
    x_github_token: str = Header(None, alias="X-Github-Token")
):
    if not authorization or not x_github_token:
        raise HTTPException(status_code=401, detail="Missing tokens")
    
    try:
        # Verify JWT
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Verify GitHub token
        async with httpx.AsyncClient() as client:
            gh_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {x_github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "TeamVault-App"
                }
            )
            
            if gh_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid GitHub token")
            
            user_data = gh_response.json()
            return {
                "valid": True,
                "user": user_data["login"],
                "email": user_data.get("email")
            }
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))