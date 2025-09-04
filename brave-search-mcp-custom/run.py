#!/usr/bin/env python3
"""Brave Search MCP Server
A Model Context Protocol server that provides access to Brave Search API
"""

import argparse
import asyncio
import os
from typing import Any

import httpx

# Load environment variables
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel

load_dotenv()

# Configuration from environment variables
BRAVE_WEB_SEARCH_LIMIT = int(os.getenv("BRAVE_WEB_SEARCH_LIMIT", "20"))
BRAVE_IMAGE_SEARCH_LIMIT = int(os.getenv("BRAVE_IMAGE_SEARCH_LIMIT", "20"))
BRAVE_NEWS_SEARCH_LIMIT = int(os.getenv("BRAVE_NEWS_SEARCH_LIMIT", "20"))
BRAVE_VIDEO_SEARCH_LIMIT = int(os.getenv("BRAVE_VIDEO_SEARCH_LIMIT", "20"))
BRAVE_SUMMARIZER_LIMIT = int(os.getenv("BRAVE_SUMMARIZER_LIMIT", "10"))


class BraveSearchResult(BaseModel):
    """Brave search result model."""

    title: str
    url: str
    description: str | None = None
    age: str | None = None
    published: str | None = None
    thumbnail: str | None = None
    language: str | None = None
    family_friendly: bool | None = None


class BraveImageResult(BaseModel):
    """Brave image search result model."""

    title: str
    url: str
    thumbnail: str | None = None
    source: str | None = None
    width: int | None = None
    height: int | None = None


class BraveNewsResult(BaseModel):
    """Brave news search result model."""

    title: str
    url: str
    description: str | None = None
    age: str | None = None
    published: str | None = None
    source: str | None = None
    thumbnail: str | None = None


class BraveVideoResult(BaseModel):
    """Brave video search result model."""

    title: str
    url: str
    thumbnail: str | None = None
    description: str | None = None
    duration: str | None = None
    published: str | None = None
    views: str | None = None


class BraveSearchMCP:
    """Brave Search MCP Server implementation."""

    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY environment variable is required")

        self.base_url = "https://api.search.brave.com/res/v1"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            },
        )

    async def web_search(
        self,
        query: str,
        count: int | None = None,
        freshness: str | None = None,
        summary: bool = False,
    ) -> list[BraveSearchResult]:
        """Perform web search using Brave Search API."""
        if count is None:
            count = BRAVE_WEB_SEARCH_LIMIT
        try:
            params = {
                "q": query,
                "count": min(count, BRAVE_WEB_SEARCH_LIMIT),  # Configurable limit
                "summary": summary,
            }

            if freshness:
                params["freshness"] = freshness

            response = await self.client.get(
                f"{self.base_url}/web/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            web_results = data.get("web", {}).get("results", [])

            for result in web_results:
                results.append(
                    BraveSearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        description=result.get("description", ""),
                        age=result.get("age"),
                        published=result.get("published"),
                        thumbnail=(
                            result.get("thumbnail", {}).get("src")
                            if result.get("thumbnail")
                            else None
                        ),
                        language=result.get("language"),
                        family_friendly=result.get("family_friendly"),
                    ),
                )

            return results

        except Exception as e:
            print(f"Error in web search: {e}")
            return []

    async def image_search(
        self,
        query: str,
        count: int | None = None,
    ) -> list[BraveImageResult]:
        """Perform image search using Brave Search API."""
        if count is None:
            count = BRAVE_IMAGE_SEARCH_LIMIT
        try:
            params = {"q": query, "count": min(count, BRAVE_IMAGE_SEARCH_LIMIT)}

            response = await self.client.get(
                f"{self.base_url}/images/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            image_results = data.get("results", [])

            for result in image_results:
                results.append(
                    BraveImageResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        thumbnail=(
                            result.get("thumbnail", {}).get("src")
                            if result.get("thumbnail")
                            else None
                        ),
                        source=result.get("source"),
                        width=result.get("properties", {}).get("width"),
                        height=result.get("properties", {}).get("height"),
                    ),
                )

            return results

        except Exception as e:
            print(f"Error in image search: {e}")
            return []

    async def news_search(
        self,
        query: str,
        count: int | None = None,
    ) -> list[BraveNewsResult]:
        """Perform news search using Brave Search API."""
        if count is None:
            count = BRAVE_NEWS_SEARCH_LIMIT
        try:
            params = {"q": query, "count": min(count, BRAVE_NEWS_SEARCH_LIMIT)}

            response = await self.client.get(
                f"{self.base_url}/news/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            news_results = data.get("results", [])

            for result in news_results:
                results.append(
                    BraveNewsResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        description=result.get("description", ""),
                        age=result.get("age"),
                        published=result.get("published"),
                        source=result.get("source"),
                        thumbnail=(
                            result.get("thumbnail", {}).get("src")
                            if result.get("thumbnail")
                            else None
                        ),
                    ),
                )

            return results

        except Exception as e:
            print(f"Error in news search: {e}")
            return []

    async def video_search(
        self,
        query: str,
        count: int | None = None,
    ) -> list[BraveVideoResult]:
        """Perform video search using Brave Search API."""
        if count is None:
            count = BRAVE_VIDEO_SEARCH_LIMIT
        try:
            params = {"q": query, "count": min(count, BRAVE_VIDEO_SEARCH_LIMIT)}

            response = await self.client.get(
                f"{self.base_url}/videos/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            video_results = data.get("results", [])

            for result in video_results:
                results.append(
                    BraveVideoResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        thumbnail=(
                            result.get("thumbnail", {}).get("src")
                            if result.get("thumbnail")
                            else None
                        ),
                        description=result.get("description", ""),
                        duration=result.get("video", {}).get("duration"),
                        published=result.get("published"),
                        views=result.get("video", {}).get("views"),
                    ),
                )

            return results

        except Exception as e:
            print(f"Error in video search: {e}")
            return []

    async def summarizer_search(
        self,
        query: str,
        count: int | None = None,
    ) -> dict[str, Any]:
        """Get AI-generated summaries using Brave's Summarizer API."""
        if count is None:
            count = BRAVE_SUMMARIZER_LIMIT
        try:
            params = {
                "q": query,
                "count": min(count, BRAVE_SUMMARIZER_LIMIT),
                "summary": True,
            }

            response = await self.client.get(
                f"{self.base_url}/web/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            # Extract summary and search results
            summary = data.get("summarizer", {})
            web_results = data.get("web", {}).get("results", [])

            return {
                "summary": summary.get("summary", ""),
                "key": summary.get("key", ""),
                "type": summary.get("type", ""),
                "results": [
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", ""),
                    }
                    for result in web_results
                ],
            }

        except Exception as e:
            print(f"Error in summarizer search: {e}")
            return {"summary": "", "results": []}


# Initialize the MCP server
mcp = FastMCP("Brave Search")
brave = BraveSearchMCP()


@mcp.tool()
async def brave_web_search(
    query: str,
    count: int | None = None,
    freshness: str | None = None,
    summary: bool = False,
) -> list[dict[str, Any]]:
    """Performs web searches using the Brave Search API and returns comprehensive search results with rich metadata.

    Args:
        query: The search query string
        count: Number of results to return (max 20)
        freshness: Freshness filter ('pd' for past day, 'pw' for past week, 'pm' for past month, 'py' for past year)
        summary: Whether to include AI summary in results

    Returns:
        List of web search results with title, url, description, and metadata

    """
    if count is None:
        count = BRAVE_WEB_SEARCH_LIMIT
    count = min(count, BRAVE_WEB_SEARCH_LIMIT)

    results = await brave.web_search(query, count, freshness, summary)
    return [result.dict() for result in results]


@mcp.tool()
async def brave_image_search(
    query: str,
    count: int | None = None,
) -> list[dict[str, Any]]:
    """Performs an image search using the Brave Search API.

    Args:
        query: The search query string for images
        count: Number of results to return (max 20)

    Returns:
        List of image search results with title, url, thumbnail, and metadata

    """
    if count is None:
        count = BRAVE_IMAGE_SEARCH_LIMIT
    count = min(count, BRAVE_IMAGE_SEARCH_LIMIT)

    results = await brave.image_search(query, count)
    return [result.dict() for result in results]


@mcp.tool()
async def brave_news_search(
    query: str,
    count: int | None = None,
) -> list[dict[str, Any]]:
    """This tool searches for news articles using Brave's News Search API based on the user's query.

    Args:
        query: The search query string for news
        count: Number of results to return (max 20)

    Returns:
        List of news search results with title, url, description, source, and metadata

    """
    if count is None:
        count = BRAVE_NEWS_SEARCH_LIMIT
    count = min(count, BRAVE_NEWS_SEARCH_LIMIT)

    results = await brave.news_search(query, count)
    return [result.dict() for result in results]


@mcp.tool()
async def brave_video_search(
    query: str,
    count: int | None = None,
) -> list[dict[str, Any]]:
    """Searches for videos using Brave's Video Search API and returns structured video results with metadata.

    Args:
        query: The search query string for videos
        count: Number of results to return (max 20)

    Returns:
        List of video search results with title, url, thumbnail, duration, and metadata

    """
    if count is None:
        count = BRAVE_VIDEO_SEARCH_LIMIT
    count = min(count, BRAVE_VIDEO_SEARCH_LIMIT)

    results = await brave.video_search(query, count)
    return [result.dict() for result in results]


@mcp.tool()
async def brave_summarizer(query: str, count: int | None = None) -> dict[str, Any]:
    """Retrieves AI-generated summaries of web search results using Brave's Summarizer API.

    Args:
        query: The search query string
        count: Number of search results to analyze for summary (max 10)

    Returns:
        Dictionary with AI-generated summary and supporting search results

    """
    if count is None:
        count = BRAVE_SUMMARIZER_LIMIT
    count = min(count, BRAVE_SUMMARIZER_LIMIT)

    return await brave.summarizer_search(query, count)


async def main():
    """Main function to run the MCP server."""
    parser = argparse.ArgumentParser(description="Brave Search MCP Server")
    parser.add_argument(
        "--transport",
        default="sse",
        choices=["stdio", "sse"],
        help="Transport method (stdio or sse)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (for sse transport)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3001,
        help="Port to bind to (for sse transport)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        await mcp.run_stdio()
    else:
        # For SSE transport, we need to create a custom FastAPI app with health endpoint
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        # Create a FastAPI app with health endpoint
        app = FastAPI(title="Brave Search MCP Server")

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return JSONResponse({"status": "healthy", "service": "brave-search-mcp"})

        # Add MCP endpoints
        @app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, request_data: dict):
            """Call MCP tool."""
            try:
                params = request_data.get("parameters", {})

                if tool_name == "brave_web_search":
                    query = params.get("query", "")
                    count = params.get("count", BRAVE_WEB_SEARCH_LIMIT)
                    freshness = params.get("freshness")
                    summary = params.get("summary", False)
                    results = await brave.web_search(query, count, freshness, summary)
                    return {"result": [result.dict() for result in results]}

                if tool_name == "brave_image_search":
                    query = params.get("query", "")
                    count = params.get("count", BRAVE_IMAGE_SEARCH_LIMIT)
                    results = await brave.image_search(query, count)
                    return {"result": [result.dict() for result in results]}

                if tool_name == "brave_news_search":
                    query = params.get("query", "")
                    count = params.get("count", BRAVE_NEWS_SEARCH_LIMIT)
                    results = await brave.news_search(query, count)
                    return {"result": [result.dict() for result in results]}

                if tool_name == "brave_video_search":
                    query = params.get("query", "")
                    count = params.get("count", BRAVE_VIDEO_SEARCH_LIMIT)
                    results = await brave.video_search(query, count)
                    return {"result": [result.dict() for result in results]}

                if tool_name == "brave_summarizer":
                    query = params.get("query", "")
                    count = params.get("count", BRAVE_SUMMARIZER_LIMIT)
                    result = await brave.summarizer_search(query, count)
                    return {"result": result}

                return {"error": f"Unknown tool: {tool_name}"}

            except Exception as e:
                return {"error": str(e)}

        @app.get("/tools")
        async def list_tools():
            """List available tools."""
            return {
                "tools": [
                    {
                        "name": "brave_web_search",
                        "description": "Perform web search using Brave Search API",
                    },
                    {
                        "name": "brave_image_search",
                        "description": "Search for images using Brave Search API",
                    },
                    {
                        "name": "brave_news_search",
                        "description": "Search for news articles using Brave Search API",
                    },
                    {
                        "name": "brave_video_search",
                        "description": "Search for videos using Brave Search API",
                    },
                    {
                        "name": "brave_summarizer",
                        "description": "Get AI-generated summaries of search results",
                    },
                ],
            }

        # Run the FastAPI app
        config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
