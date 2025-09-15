"""Brave Search MCP Server - Simple HTTP implementation for demo"""

import os
from datetime import datetime
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Brave Search MCP Server")

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class ToolRequest(BaseModel):
    tool: str
    parameters: dict[str, Any]
    timestamp: str


@app.get("/health")
async def health():
    return {"status": "healthy", "server": "brave_search", "timestamp": datetime.utcnow().isoformat()}


@app.post("/tools/brave_web_search")
async def brave_web_search(request: ToolRequest):
    """Brave web search tool endpoint"""
    if not BRAVE_API_KEY:
        raise HTTPException(status_code=500, detail="BRAVE_API_KEY not configured")
    
    params = request.parameters
    query = params.get("query", "")
    count = params.get("count", 20)
    freshness = params.get("freshness")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    
    search_params = {
        "q": query,
        "count": count,
    }
    
    if freshness:
        search_params["freshness"] = freshness
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                BRAVE_SEARCH_URL,
                headers=headers,
                params=search_params,
                timeout=30.0,
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract web results
            web_results = []
            if "web" in data and "results" in data["web"]:
                for result in data["web"]["results"][:count]:
                    web_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", ""),
                        "age": result.get("age"),
                        "language": result.get("language"),
                    })
            
            return {
                "tool": "brave_web_search",
                "result": {
                    "query": query,
                    "count": len(web_results),
                    "results": web_results,
                },
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Brave API error: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "brave_web_search",
                "description": "Search the web using Brave Search API",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "count": {"type": "integer", "default": 20},
                    "freshness": {"type": "string", "enum": ["pd", "pw", "pm", "py"]},
                },
            }
        ]
    }


if __name__ == "__main__":
    print(f"Starting Brave Search MCP Server on port 3001")
    print(f"BRAVE_API_KEY configured: {'Yes' if BRAVE_API_KEY else 'No'}")
    uvicorn.run(app, host="0.0.0.0", port=3001)