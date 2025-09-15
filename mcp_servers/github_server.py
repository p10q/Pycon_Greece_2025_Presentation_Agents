"""GitHub MCP Server - Simple HTTP implementation for demo"""

import os
from datetime import datetime
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="GitHub MCP Server")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"


class ToolRequest(BaseModel):
    tool: str
    parameters: dict[str, Any]
    timestamp: str


def get_headers():
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MCP-GitHub-Server",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


@app.get("/health")
async def health():
    return {"status": "healthy", "server": "github", "timestamp": datetime.utcnow().isoformat()}


@app.post("/tools/search_repositories")
async def search_repositories(request: ToolRequest):
    """Search GitHub repositories"""
    params = request.parameters
    query = params.get("query", "")
    sort = params.get("sort", "stars")
    order = params.get("order", "desc")
    per_page = params.get("per_page", 10)
    
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/search/repositories",
                headers=get_headers(),
                params={
                    "q": query,
                    "sort": sort,
                    "order": order,
                    "per_page": per_page,
                },
                timeout=30.0,
            )
            
            if response.status_code == 403:
                raise HTTPException(status_code=403, detail="GitHub API rate limit exceeded")
            
            response.raise_for_status()
            data = response.json()
            
            repositories = []
            for repo in data.get("items", []):
                repositories.append({
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "description": repo.get("description"),
                    "url": repo.get("html_url"),
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "language": repo.get("language"),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                })
            
            return {
                "tool": "search_repositories",
                "result": {
                    "query": query,
                    "total_count": data.get("total_count", 0),
                    "count": len(repositories),
                    "repositories": repositories,
                },
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/tools/get_repository")
async def get_repository(request: ToolRequest):
    """Get repository details"""
    params = request.parameters
    owner = params.get("owner", "")
    repo = params.get("repo", "")
    
    if not owner or not repo:
        raise HTTPException(status_code=400, detail="Owner and repo parameters are required")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
                headers=get_headers(),
                timeout=30.0,
            )
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Repository not found")
            elif response.status_code == 403:
                raise HTTPException(status_code=403, detail="GitHub API rate limit exceeded")
            
            response.raise_for_status()
            repo_data = response.json()
            
            return {
                "tool": "get_repository",
                "result": {
                    "name": repo_data.get("name"),
                    "full_name": repo_data.get("full_name"),
                    "description": repo_data.get("description"),
                    "url": repo_data.get("html_url"),
                    "stars": repo_data.get("stargazers_count"),
                    "forks": repo_data.get("forks_count"),
                    "language": repo_data.get("language"),
                    "created_at": repo_data.get("created_at"),
                    "updated_at": repo_data.get("updated_at"),
                    "topics": repo_data.get("topics", []),
                    "license": repo_data.get("license"),
                },
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repository: {str(e)}")


@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "search_repositories",
                "description": "Search GitHub repositories",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "sort": {"type": "string", "enum": ["stars", "forks", "updated"], "default": "stars"},
                    "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                    "per_page": {"type": "integer", "default": 10, "max": 100},
                },
            },
            {
                "name": "get_repository",
                "description": "Get detailed repository information",
                "parameters": {
                    "owner": {"type": "string", "required": True},
                    "repo": {"type": "string", "required": True},
                },
            },
        ]
    }


if __name__ == "__main__":
    print(f"Starting GitHub MCP Server on port 3002")
    print(f"GITHUB_TOKEN configured: {'Yes' if GITHUB_TOKEN else 'No'}")
    uvicorn.run(app, host="0.0.0.0", port=3002)