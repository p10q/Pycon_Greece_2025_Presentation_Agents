"""Hacker News MCP Server - Simple HTTP implementation for demo"""

from datetime import datetime
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Hacker News MCP Server")

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


class ToolRequest(BaseModel):
    tool: str
    parameters: dict[str, Any]
    timestamp: str


@app.get("/health")
async def health():
    return {"status": "healthy", "server": "hacker_news", "timestamp": datetime.utcnow().isoformat()}


@app.post("/tools/get_stories")
async def get_stories(request: ToolRequest):
    """Get HN stories by type"""
    params = request.parameters
    story_type = params.get("story_type", "topstories")
    limit = params.get("limit", 10)
    
    # Map story types to HN API endpoints
    story_endpoints = {
        "topstories": "topstories",
        "newstories": "newstories",
        "beststories": "beststories",
        "askstories": "askstories",
        "showstories": "showstories",
        "jobstories": "jobstories",
    }
    
    endpoint = story_endpoints.get(story_type, "topstories")
    
    try:
        async with httpx.AsyncClient() as client:
            # Get story IDs
            response = await client.get(f"{HN_API_BASE}/{endpoint}.json", timeout=30.0)
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            # Fetch story details
            stories = []
            for story_id in story_ids:
                try:
                    story_response = await client.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=10.0)
                    if story_response.status_code == 200:
                        story_data = story_response.json()
                        if story_data:
                            stories.append({
                                "id": story_data.get("id"),
                                "title": story_data.get("title", ""),
                                "url": story_data.get("url", ""),
                                "score": story_data.get("score", 0),
                                "by": story_data.get("by", ""),
                                "time": story_data.get("time"),
                                "descendants": story_data.get("descendants", 0),
                                "type": story_data.get("type", ""),
                            })
                except Exception:
                    continue
            
            return {
                "tool": "get_stories",
                "result": {
                    "story_type": story_type,
                    "count": len(stories),
                    "stories": stories,
                },
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stories: {str(e)}")


@app.post("/tools/search_stories")
async def search_stories(request: ToolRequest):
    """Search HN stories using Algolia"""
    params = request.parameters
    query = params.get("query", "")
    limit = params.get("limit", 20)
    
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                ALGOLIA_SEARCH_URL,
                params={
                    "query": query,
                    "hitsPerPage": limit,
                    "tags": "story",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            
            data = response.json()
            hits = data.get("hits", [])
            
            stories = []
            for hit in hits:
                stories.append({
                    "id": hit.get("objectID"),
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "score": hit.get("points", 0),
                    "by": hit.get("author", ""),
                    "time": hit.get("created_at_i"),
                    "num_comments": hit.get("num_comments", 0),
                })
            
            return {
                "tool": "search_stories",
                "result": {
                    "query": query,
                    "count": len(stories),
                    "stories": stories,
                },
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "get_stories",
                "description": "Get Hacker News stories by type",
                "parameters": {
                    "story_type": {
                        "type": "string",
                        "enum": ["topstories", "newstories", "beststories", "askstories", "showstories", "jobstories"],
                        "default": "topstories",
                    },
                    "limit": {"type": "integer", "default": 10},
                },
            },
            {
                "name": "search_stories",
                "description": "Search Hacker News stories",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ]
    }


if __name__ == "__main__":
    print("Starting Hacker News MCP Server on port 3003")
    uvicorn.run(app, host="0.0.0.0", port=3003)