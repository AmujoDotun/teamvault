const apiUrl = "http://localhost:8000";

class GitHubManager {
  constructor() {
    console.log("Initializing GitHubManager...");
    this.baseUrl = `${apiUrl}/api/v1`;
    this.currentOrg = null;
    this.init();
  }

  async init() {
    const user = await this.verifyUser();

    console.log({user})
    if (!user) {
      console.log("User not verified, redirecting to login...");
      window.location.href = `${this.apiUrl}/auth/login`;
      return;
    }
    await this.loadOrganizations();
  }

  async loadOrganizations() {
    try {
      console.log("Fetching organizations...");
      const response = await fetch(`${this.baseUrl}/orgs`, {
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });
      console.log("Organizations response:", response.status);
      if (!response.ok) {
        throw new Error(`Failed to load organizations: ${response.status}`);
      }
      const data = await response.json();
      console.log("Organizations data:", data);
      this.renderOrgSelector(data.organizations || []);
    } catch (error) {
      console.error("Failed to load organizations:", error);
      document.getElementById("org-selector").innerHTML =
        "Error loading organizations";
    }
  }


  renderOrgSelector(organizations) {  
    const orgSelector = document.getElementById("org-selector");
    orgSelector.innerHTML = ""; // Clear existing options

    organizations.forEach((org) => {
      const option = document.createElement("option");
      option.value = org.login;
      option.textContent = org.login;
      orgSelector.appendChild(option);
    });

    orgSelector.addEventListener("change", (event) => {
      this.currentOrg = event.target.value;
      console.log("Selected organization:", this.currentOrg);
      this.loadRepositories(this.currentOrg);
    });
  }

  verifyUser() {
    const user = fetch(`${apiUrl}/auth/verify`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    });

    return user 
  }
}

// Initialize the app
document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM loaded, starting app...");
  new GitHubManager();
});
