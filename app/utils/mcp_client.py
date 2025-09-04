"""MCP client utilities for connecting to MCP servers."""

from datetime import datetime
from typing import Any

import httpx

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class MCPClient:
    """Client for communicating with MCP servers."""

    def __init__(self, server_url: str, server_name: str) -> None:
        """Initialize MCP client.

        Args:
            server_url: URL of the MCP server
            server_name: Name of the MCP server for logging

        """
        self.server_url = server_url.rstrip("/")
        self.server_name = server_name
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """Check if the MCP server is healthy.

        Returns:
            True if server is healthy, False otherwise

        """
        try:
            response = await self.client.get(f"{self.server_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(
                "MCP server health check failed",
                server=self.server_name,
                url=self.server_url,
                error=str(e),
            )
            return False

    async def call_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            parameters: Parameters to pass to the tool

        Returns:
            Tool execution result

        Raises:
            httpx.HTTPError: If the request fails

        """
        payload = {
            "tool": tool_name,
            "parameters": parameters or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Calling MCP tool",
            server=self.server_name,
            tool=tool_name,
            parameters=parameters,
        )

        try:
            response = await self.client.post(
                f"{self.server_url}/tools/{tool_name}",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            logger.info(
                "MCP tool call successful",
                server=self.server_name,
                tool=tool_name,
                status_code=response.status_code,
            )

            return result

        except httpx.HTTPError as e:
            logger.error(
                "MCP tool call failed",
                server=self.server_name,
                tool=tool_name,
                error=str(e),
                status_code=(
                    getattr(e.response, "status_code", None)
                    if hasattr(e, "response") and e.response
                    else None
                ),
            )
            raise
        except Exception as e:
            logger.error(
                "MCP tool call failed with unexpected error",
                server=self.server_name,
                tool=tool_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def list_tools(self) -> list:
        """List available tools on the MCP server.

        Returns:
            List of available tools

        """
        try:
            response = await self.client.get(f"{self.server_url}/tools")
            response.raise_for_status()
            return response.json().get("tools", [])
        except httpx.HTTPError as e:
            logger.error(
                "Failed to list MCP tools",
                server=self.server_name,
                error=str(e),
            )
            return []


class MCPClientManager:
    """Manager for multiple MCP clients."""

    def __init__(self) -> None:
        """Initialize MCP client manager."""
        self.clients: dict[str, MCPClient] = {}

    async def __aenter__(self) -> "MCPClientManager":
        """Async context manager entry."""
        # Initialize all MCP clients (only if URL is provided)
        client_configs = {
            "brave_search": settings.brave_search_mcp_url,
            "github": settings.github_mcp_url,
            "hacker_news": settings.hacker_news_mcp_url,
            "filesystem": settings.filesystem_mcp_url,
        }

        self.clients = {}
        for name, url in client_configs.items():
            if url and url.strip():  # Only create client if URL is provided
                self.clients[name] = MCPClient(url, name)

        # Enter context for all clients
        for client in self.clients.values():
            await client.__aenter__()

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Exit context for all clients
        for client in self.clients.values():
            await client.__aexit__(exc_type, exc_val, exc_tb)

    def get_client(self, server_name: str) -> MCPClient | None:
        """Get an MCP client by server name.

        Args:
            server_name: Name of the MCP server

        Returns:
            MCP client instance or None if not found

        """
        return self.clients.get(server_name)

    async def health_check_all(self) -> dict:
        """Check health of all MCP servers.

        Returns:
            Dictionary mapping server names to health status

        """
        results = {}
        for name, client in self.clients.items():
            results[name] = await client.health_check()
        return results
