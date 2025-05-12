from fastapi import APIRouter, Depends, Request, HTTPException
import httpx
from typing import Optional
from ..models.user import User
from ..utils.auth import get_current_user

router = APIRouter()

@router.get("/orgs")
async def list_organizations(request: Request):

    token = request.cookies.get("jwt_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    current_user = await get_current_user(token)
      
    print(f"Current user:", {"current_user": current_user.username})
       
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/orgs",
            headers={
                "Authorization": f"Bearer {current_user.access_token}",
                "Accept": "application/json"
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch organizations")
        
        orgs = response.json()

        print(f"Organizations:", orgs)
        if not orgs:
            return {"message": "You are not a member of any organizations", "organizations": []}
        return {"message": "Organizations fetched successfully", "organizations": orgs}

@router.get("/orgs/{org}/members")
async def list_org_members(org: str, role: Optional[str] = None, current_user: User = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        # First verify organization exists and user has access
        org_response = await client.get(
            f"https://api.github.com/orgs/{org}",
            headers={
                "Authorization": f"Bearer {current_user.access_token}",
                "Accept": "application/json"
            }
        )
        if org_response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Organization '{org}' not found")
        if org_response.status_code != 200:
            raise HTTPException(status_code=403, detail="You don't have access to this organization")

        # Then get members
        params = {"role": role} if role else {}
        response = await client.get(
            f"https://api.github.com/orgs/{org}/members",
            params=params,
            headers={
                "Authorization": f"Bearer {current_user.access_token}",
                "Accept": "application/json"
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch organization members")
        
        members = response.json()
        return {"message": "Members fetched successfully", "members": members}

@router.get("/orgs/{org}/teams")
async def list_org_teams(org: str, current_user: User = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/orgs/{org}/teams",
            headers={
                "Authorization": f"Bearer {current_user.access_token}",
                "Accept": "application/json"
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch organization teams")
        return response.json()

@router.get("/orgs/{org}/repos")
async def list_org_repos(org: str, current_user: User = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/orgs/{org}/repos",
            headers={
                "Authorization": f"Bearer {current_user.access_token}",
                "Accept": "application/json"
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch organization repositories")
        return response.json()

@router.put("/orgs/{org}/members/{username}/role")
async def update_member_role(
    org: str, 
    username: str, 
    role: str,
    current_user: User = Depends(get_current_user)
):
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"https://api.github.com/orgs/{org}/memberships/{username}",
            json={"role": role},
            headers={
                "Authorization": f"Bearer {current_user.access_token}",
                "Accept": "application/json"
            }
        )
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail="Failed to update member role")
        return response.json()

@router.delete("/orgs/{org}/members/{username}")
async def remove_org_member(
    org: str,
    username: str,
    current_user: User = Depends(get_current_user)
):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"https://api.github.com/orgs/{org}/memberships/{username}",
            headers={
                "Authorization": f"Bearer {current_user.access_token}",
                "Accept": "application/json"
            }
        )
        if response.status_code != 204:
            raise HTTPException(status_code=400, detail="Failed to remove member")
        return {"status": "success", "message": f"Removed {username} from {org}"}