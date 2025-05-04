import requests
import os
import json
from typing import Optional

class GitHubAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.jwt_token = os.getenv("TOKEN")
        if not self.jwt_token:
            raise ValueError("Please set TOKEN environment variable")
        
        self.headers = {
            "Authorization": f"Bearer {self.jwt_token}",  # Use JWT token format
            "Accept": "application/json"
        }

    def test_organizations(self):
        """Test listing organizations"""
        response = requests.get(
            f"{self.base_url}/api/v1/orgs",
            headers=self.headers
        )
        if response.status_code == 401:
            print("Authentication failed. Make sure you're using the JWT token, not the GitHub token")
            return response.json()
            
        print("\n=== Organizations ===")
        print(json.dumps(response.json(), indent=2))
        return response.json()

    def test_org_members(self, org_name: str, role: Optional[str] = None):
        """Test listing organization members"""
        params = {"role": role} if role else {}
        response = requests.get(
            f"{self.base_url}/api/v1/orgs/{org_name}/members",
            headers=self.headers,
            params=params
        )
        print(f"\n=== Members of {org_name} ===")
        print(json.dumps(response.json(), indent=2))
        return response.json()

    def test_org_teams(self, org_name: str):
        """Test listing organization teams"""
        response = requests.get(
            f"{self.base_url}/api/v1/orgs/{org_name}/teams",
            headers=self.headers
        )
        print(f"\n=== Teams in {org_name} ===")
        print(json.dumps(response.json(), indent=2))
        return response.json()

    def test_org_repos(self, org_name: str):
        """Test listing organization repositories"""
        response = requests.get(
            f"{self.base_url}/api/v1/orgs/{org_name}/repos",
            headers=self.headers
        )
        repos = response.json()
        print(f"\n=== Repositories in {org_name} ===")
        for repo in repos:
            print(f"- {repo['name']} ({repo['visibility']})")
            print(f"  Language: {repo['language']}")
            print(f"  Updated: {repo['updated_at']}")
            print(f"  Permissions: {', '.join(k for k, v in repo['permissions'].items() if v)}")
        return repos

    def remove_org_member(self, org_name: str, username: str):
        """Remove a member from organization"""
        response = requests.delete(
            f"{self.base_url}/api/v1/orgs/{org_name}/members/{username}",
            headers=self.headers
        )
        print(f"\n=== Remove {username} from {org_name} ===")
        print(json.dumps(response.json(), indent=2))
        return response.json()

    def check_member_permissions(self, org_name: str):
        """Check member management permissions without making changes"""
        response = requests.get(
            f"{self.base_url}/api/v1/orgs/{org_name}",
            headers=self.headers
        )
        org_data = response.json()
        
        print("\n=== Organization Permissions ===")
        print(f"Your role: {org_data.get('role', 'unknown')}")
        print(f"Can manage members: {org_data.get('permissions', {}).get('admin', False)}")
        return org_data

    def test_all_endpoints(self, org_name: str = None):
        """Test all endpoints with proper error handling"""
        try:
            # Test organizations
            orgs = self.test_organizations()
            if not orgs.get("organizations"):
                print("No organizations found")
                return

            # Use provided org_name or first organization
            org_name = org_name or orgs["organizations"][0]["login"]
            print(f"\nTesting with organization: {org_name}")

            # Test basic info
            members = self.test_org_members(org_name)
            print(f"\nMembers count: {len(members)}")
            
            teams = self.test_org_teams(org_name)
            print(f"Teams count: {len(teams)}")
            
            repos = self.test_org_repos(org_name)
            print(f"Repositories count: {len(repos)}")

            # Example of role management (uncomment to test)
            # self.test_update_member_role(org_name, "some_username", "admin")
            # self.remove_org_member(org_name, "some_username")

            # Check permissions safely
            self.check_member_permissions(org_name)
            
            # Comment out dangerous operations
            # self.remove_org_member(org_name, "some_username")  # Dangerous!

        except requests.exceptions.RequestException as e:
            print(f"Error during testing: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    tester = GitHubAPITester()
    tester.test_all_endpoints("avancerTeams")