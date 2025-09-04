#!/usr/bin/env python3
"""Hacker News MCP Server
A Model Context Protocol server that provides access to Hacker News API
"""

import argparse
import asyncio
from typing import Any

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel


class HackerNewsStory(BaseModel):
    """Hacker News story model."""

    id: int
    title: str
    url: str | None = None
    text: str | None = None
    score: int | None = None
    by: str | None = None
    time: int | None = None
    descendants: int | None = None
    kids: list[int] | None = None
    type: str = "story"


class HackerNewsMCP:
    """Hacker News MCP Server implementation."""

    def __init__(self):
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_story(self, story_id: int) -> HackerNewsStory | None:
        """Get a single story by ID."""
        try:
            response = await self.client.get(f"{self.base_url}/item/{story_id}.json")
            if response.status_code == 200:
                data = response.json()
                if data:
                    return HackerNewsStory(**data)
            return None
        except Exception as e:
            print(f"Error fetching story {story_id}: {e}")
            return None

    async def get_story_ids(self, story_type: str) -> list[int]:
        """Get story IDs for a given type."""
        try:
            response = await self.client.get(f"{self.base_url}/{story_type}.json")
            if response.status_code == 200:
                return response.json() or []
            return []
        except Exception as e:
            print(f"Error fetching {story_type} story IDs: {e}")
            return []

    async def get_stories(
        self,
        story_type: str = "topstories",
        limit: int = 30,
    ) -> list[HackerNewsStory]:
        """Get stories by type with limit."""
        story_ids = await self.get_story_ids(story_type)
        stories = []

        # Limit the number of concurrent requests
        semaphore = asyncio.Semaphore(10)

        async def fetch_story(story_id: int) -> HackerNewsStory | None:
            async with semaphore:
                return await self.get_story(story_id)

        # Fetch stories concurrently but limit to requested amount
        tasks = [fetch_story(story_id) for story_id in story_ids[:limit]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, HackerNewsStory):
                stories.append(result)

        return stories

    async def search_stories(
        self,
        query: str,
        limit: int = 20,
    ) -> list[HackerNewsStory]:
        """Search stories by query (simple title matching)."""
        # Get top stories and filter by query
        stories = await self.get_stories("topstories", limit * 3)  # Get more to filter

        query_lower = query.lower()
        matching_stories = []

        for story in stories:
            if query_lower in story.title.lower() or (
                story.text and query_lower in story.text.lower()
            ):
                matching_stories.append(story)
                if len(matching_stories) >= limit:
                    break

        return matching_stories


# Initialize the MCP server
mcp = FastMCP("Hacker News")
hn = HackerNewsMCP()


@mcp.tool()
async def get_stories(
    story_type: str = "topstories",
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Get Hacker News stories by type.

    Args:
        story_type: Type of stories to fetch (topstories, newstories, beststories, askstories, showstories, jobstories)
        limit: Maximum number of stories to return (default: 30, max: 100)

    Returns:
        List of story dictionaries with id, title, url, score, author, etc.

    """
    limit = min(limit, 100)

    valid_types = [
        "topstories",
        "newstories",
        "beststories",
        "askstories",
        "showstories",
        "jobstories",
    ]
    if story_type not in valid_types:
        story_type = "topstories"

    stories = await hn.get_stories(story_type, limit)
    return [story.model_dump() for story in stories]


@mcp.tool()
async def get_story(story_id: int) -> dict[str, Any] | None:
    """Get a specific Hacker News story by ID.

    Args:
        story_id: The ID of the story to fetch

    Returns:
        Story dictionary with all available fields or None if not found

    """
    story = await hn.get_story(story_id)
    return story.model_dump() if story else None


@mcp.tool()
async def search_stories(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search Hacker News stories by query.

    Args:
        query: Search query to match in story titles and text
        limit: Maximum number of results to return (default: 20, max: 50)

    Returns:
        List of matching story dictionaries

    """
    limit = min(limit, 50)

    stories = await hn.search_stories(query, limit)
    return [story.model_dump() for story in stories]


@mcp.tool()
async def get_trending_topics(limit: int = 10) -> list[dict[str, Any]]:
    """Get trending topics from top stories.

    Args:
        limit: Number of top stories to analyze for trends (default: 10, max: 50)

    Returns:
        List of trending topics with story counts and examples

    """
    limit = min(limit, 50)

    stories = await hn.get_stories("topstories", limit)

    # Simple keyword extraction and counting
    word_counts = {}
    topic_stories = {}

    for story in stories:
        words = story.title.lower().split()
        for word in words:
            # Filter out common words and short words
            if len(word) > 3 and word not in [
                "with",
                "from",
                "that",
                "this",
                "they",
                "have",
                "been",
                "were",
                "will",
                "your",
            ]:
                word_counts[word] = word_counts.get(word, 0) + 1
                if word not in topic_stories:
                    topic_stories[word] = []
                topic_stories[word].append(
                    {"id": story.id, "title": story.title, "score": story.score},
                )

    # Sort by frequency and return top topics
    trending = []
    for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]:
        trending.append(
            {
                "topic": word,
                "count": count,
                "stories": topic_stories[word][:3],  # Top 3 stories for this topic
            },
        )

    return trending


async def main():
    """Main function to run the MCP server."""
    parser = argparse.ArgumentParser(description="Hacker News MCP Server")
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
        default=3003,
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
        app = FastAPI(title="Hacker News MCP Server")

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return JSONResponse({"status": "healthy", "service": "hackernews-mcp"})

        # Add MCP endpoints - this is a simplified approach
        @app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, request_data: dict):
            """Call MCP tool."""
            try:
                if tool_name == "get_stories":
                    params = request_data.get("parameters", {})
                    story_type = params.get("story_type", "topstories")
                    limit = params.get("limit", 30)
                    stories = await hn.get_stories(story_type, limit)
                    return {"result": [story.model_dump() for story in stories]}
                if tool_name == "get_story":
                    params = request_data.get("parameters", {})
                    story_id = params.get("story_id")
                    if story_id:
                        story = await hn.get_story(story_id)
                        return {"result": story.model_dump() if story else None}
                    return {"error": "story_id required"}
                if tool_name == "search_stories":
                    params = request_data.get("parameters", {})
                    query = params.get("query", "")
                    limit = params.get("limit", 20)
                    stories = await hn.search_stories(query, limit)
                    return {"result": [story.model_dump() for story in stories]}
                if tool_name == "get_trending_topics":
                    params = request_data.get("parameters", {})
                    limit = params.get("limit", 10)
                    # Use the existing get_trending_topics function
                    trending = await get_trending_topics(limit)
                    return {"result": trending}
                return {"error": f"Unknown tool: {tool_name}"}
            except Exception as e:
                return {"error": str(e)}

        @app.get("/tools")
        async def list_tools():
            """List available tools."""
            return {
                "tools": [
                    {
                        "name": "get_stories",
                        "description": "Get Hacker News stories by type",
                    },
                    {
                        "name": "get_story",
                        "description": "Get a specific Hacker News story by ID",
                    },
                    {
                        "name": "search_stories",
                        "description": "Search Hacker News stories by query",
                    },
                    {
                        "name": "get_trending_topics",
                        "description": "Get trending topics from top stories",
                    },
                ],
            }

        # Run the FastAPI app
        config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
