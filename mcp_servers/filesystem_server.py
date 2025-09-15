"""Filesystem MCP Server - Simple HTTP implementation for demo"""

import os
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Filesystem MCP Server")

# Define allowed paths
ALLOWED_PATHS = [
    "/app/data",
    "/app/examples",
    os.path.join(os.getcwd(), "data"),
    os.path.join(os.getcwd(), "examples"),
]


class ToolRequest(BaseModel):
    tool: str
    parameters: dict
    timestamp: str


def is_path_allowed(path: str) -> bool:
    """Check if a path is within allowed directories"""
    abs_path = os.path.abspath(path)
    for allowed in ALLOWED_PATHS:
        if os.path.exists(allowed) and abs_path.startswith(os.path.abspath(allowed)):
            return True
    return False


@app.get("/health")
async def health():
    return {"status": "healthy", "server": "filesystem", "timestamp": datetime.utcnow().isoformat()}


@app.post("/tools/read_file")
async def read_file(request: ToolRequest):
    """Read file contents"""
    params = request.parameters
    file_path = params.get("path", "")
    
    if not file_path:
        raise HTTPException(status_code=400, detail="Path parameter is required")
    
    if not is_path_allowed(file_path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
    try:
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        content = path.read_text(encoding='utf-8')
        
        return {
            "tool": "read_file",
            "result": {
                "path": file_path,
                "content": content,
                "size": len(content),
                "lines": content.count('\n') + 1,
            },
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@app.post("/tools/list_directory")
async def list_directory(request: ToolRequest):
    """List directory contents"""
    params = request.parameters
    dir_path = params.get("path", ".")
    
    if not is_path_allowed(dir_path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
    try:
        path = Path(dir_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        if not path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        items = []
        for item in path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
            })
        
        return {
            "tool": "list_directory",
            "result": {
                "path": dir_path,
                "count": len(items),
                "items": items,
            },
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list directory: {str(e)}")


@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "parameters": {
                    "path": {"type": "string", "required": True},
                },
            },
            {
                "name": "list_directory",
                "description": "List contents of a directory",
                "parameters": {
                    "path": {"type": "string", "default": "."},
                },
            },
        ]
    }


if __name__ == "__main__":
    print("Starting Filesystem MCP Server on port 3004")
    print(f"Allowed paths: {ALLOWED_PATHS}")
    uvicorn.run(app, host="0.0.0.0", port=3004)