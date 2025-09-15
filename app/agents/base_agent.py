"""Base agent class with common functionality."""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.bedrock import BedrockConverseModel

from ..models.schemas import AgentMessage
from ..utils import MCPClientManager, get_logger, settings

logger = get_logger(__name__)

# Environment variable configuration
BRAVE_WEB_SEARCH_LIMIT = int(os.getenv("BRAVE_WEB_SEARCH_LIMIT", "20"))


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(self, agent_name: str, system_prompt: str) -> None:
        """Initialize the base agent.

        Args:
            agent_name: Name of the agent
            system_prompt: System prompt for the agent

        """
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.mcp_manager: MCPClientManager | None = None

        # Initialize Pydantic-AI agent with Bedrock
        self.agent = Agent(
            model=BedrockConverseModel(model_name=settings.anthropic_model),
            system_prompt=self.system_prompt,
        )

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register MCP tools with the agent."""

        @self.agent.tool
        async def search_brave(ctx: RunContext[Any], query: str, freshness: str = "pm"):
            """Search using Brave Search MCP server with freshness filter.

            Args:
                ctx: Pydantic-AI run context
                query: Search query
                freshness: Time filter (pd=24h, pw=7d, pm=31d, py=365d)

            Returns:
                Search results from Brave Search

            """
            if not self.mcp_manager:
                return {"error": "MCP manager not initialized"}

            client = self.mcp_manager.get_client("brave_search")
            if not client:
                return {"error": "Brave Search MCP client not available"}

            try:
                result = await client.call_tool(
                    "brave_web_search",
                    {
                        "query": query,
                        "freshness": freshness,
                        "count": BRAVE_WEB_SEARCH_LIMIT,
                    },
                )
                return result
            except Exception as e:
                logger.error(f"Brave search failed: {e}")
                # Return a more specific error for better fallback handling
                return {"error": "mcp_connection_failed", "details": str(e)}

        @self.agent.tool
        async def get_hacker_news_stories(
            ctx: RunContext[Any],
            story_type: str = "top",
            limit: int = 10,
        ):
            """Get stories from Hacker News MCP server.

            Args:
                ctx: Pydantic-AI run context
                story_type: Type of stories (top, new, best, ask, show, job)
                limit: Number of stories to fetch

            Returns:
                Hacker News stories

            """
            if not self.mcp_manager:
                return {"error": "MCP manager not initialized"}

            client = self.mcp_manager.get_client("hacker_news")
            if not client:
                return {"error": "Hacker News MCP client not available"}

            try:
                # Map shorthand to Hacker News API story types
                type_map = {
                    "top": "topstories",
                    "new": "newstories",
                    "best": "beststories",
                    "ask": "askstories",
                    "show": "showstories",
                    "job": "jobstories",
                }
                hn_story_type = type_map.get(story_type.lower(), story_type)

                result = await client.call_tool(
                    "get_stories",
                    {"story_type": hn_story_type, "limit": limit},
                )
                return result
            except Exception as e:
                logger.error(f"Hacker News fetch failed: {e}")
                # Return a more specific error for better fallback handling
                return {"error": "mcp_connection_failed", "details": str(e)}

        @self.agent.tool
        async def search_github_repos(
            ctx: RunContext[Any],
            query: str,
            sort: str = "stars",
            order: str = "desc",
            limit: int = 10,
        ):
            """Search GitHub repositories using GitHub MCP server.

            Args:
                ctx: Pydantic-AI run context
                query: Search query
                sort: Sort field (stars, forks, updated)
                order: Sort order (asc, desc)
                limit: Number of results to return

            Returns:
                GitHub repository search results

            """
            if not self.mcp_manager:
                return {"error": "MCP manager not initialized"}

            client = self.mcp_manager.get_client("github")
            if not client:
                return {"error": "GitHub MCP client not available"}

            try:
                result = await client.call_tool(
                    "search_repositories",
                    {
                        "query": query,
                        "sort": sort,
                        "order": order,
                        "per_page": limit,
                    },
                )
                return result
            except Exception as e:
                logger.error(f"GitHub search failed: {e}")
                return {"error": str(e)}

        @self.agent.tool
        async def get_github_repo_details(ctx: RunContext[Any], owner: str, repo: str):
            """Get detailed information about a GitHub repository.

            Args:
                ctx: Pydantic-AI run context
                owner: Repository owner
                repo: Repository name

            Returns:
                Detailed repository information

            """
            if not self.mcp_manager:
                return {"error": "MCP manager not initialized"}

            client = self.mcp_manager.get_client("github")
            if not client:
                return {"error": "GitHub MCP client not available"}

            try:
                result = await client.call_tool(
                    "get_repository",
                    {"owner": owner, "repo": repo},
                )
                return result
            except Exception as e:
                logger.error(f"GitHub repo details fetch failed: {e}")
                return {"error": str(e)}

        @self.agent.tool
        async def read_file(ctx: RunContext[Any], file_path: str):
            """Read a file using the Filesystem MCP server.

            Args:
                ctx: Pydantic-AI run context
                file_path: Path to the file to read

            Returns:
                File contents

            """
            if not self.mcp_manager:
                return {"error": "MCP manager not initialized"}

            client = self.mcp_manager.get_client("filesystem")
            if not client:
                return {"error": "Filesystem MCP client not available"}

            try:
                result = await client.call_tool("read_file", {"path": file_path})
                return result
            except Exception as e:
                logger.error(f"File read failed: {e}")
                return {"error": str(e)}

    async def initialize(self, mcp_manager: MCPClientManager) -> None:
        """Initialize the agent with MCP manager.

        Args:
            mcp_manager: MCP client manager instance

        """
        self.mcp_manager = mcp_manager
        logger.info(f"Agent {self.agent_name} initialized")

    async def send_message_to_agent(
        self,
        recipient: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> AgentMessage:
        """Send a message to another agent (A2A communication).

        Args:
            recipient: Name of the recipient agent
            message_type: Type of message
            payload: Message payload

        Returns:
            Agent message object

        """
        message = AgentMessage(
            sender_agent=self.agent_name,
            recipient_agent=recipient,
            message_type=message_type,
            payload=payload,
        )

        logger.info(
            "Sending A2A message",
            sender=self.agent_name,
            recipient=recipient,
            message_type=message_type,
        )

        return message

    @abstractmethod
    async def process_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Process a request. Must be implemented by subclasses.

        Args:
            request_data: Request data to process

        Returns:
            Processing result

        """

    async def health_check(self) -> dict[str, str]:
        """Perform health check for the agent.

        Returns:
            Health check results

        """
        status = "healthy"
        details = f"Agent {self.agent_name} is operational"

        if not self.mcp_manager:
            status = "degraded"
            details = "MCP manager not initialized"

        return {
            "status": status,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }
