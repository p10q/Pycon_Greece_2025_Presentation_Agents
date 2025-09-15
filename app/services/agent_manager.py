"""Agent manager service for coordinating multiple agents."""

from datetime import datetime
from typing import Any

from ..agents import EntryAgent, GeneralAgent, SpecialistAgent
from ..utils import MCPClientManager, get_logger
from .a2a_service import A2AService

logger = get_logger(__name__)


class AgentManager:
    """Manager for coordinating multiple agents and their interactions."""

    def __init__(self) -> None:
        """Initialize the agent manager."""
        self.entry_agent: EntryAgent | None = None
        self.specialist_agent: SpecialistAgent | None = None
        self.a2a_service: A2AService | None = None
        self.mcp_manager: MCPClientManager | None = None
        self.initialized = False
        self.general_agent: GeneralAgent | None = None

    async def initialize(self) -> None:
        """Initialize all agents and services."""
        try:
            logger.info("Initializing agent manager")

            # Initialize MCP client manager
            self.mcp_manager = MCPClientManager()
            await self.mcp_manager.__aenter__()

            # Initialize A2A service
            self.a2a_service = A2AService()
            # Start A2A service to indicate HTTP endpoints will be available
            await self.a2a_service.start_server()

            # Initialize agents
            self.entry_agent = EntryAgent()
            self.specialist_agent = SpecialistAgent()
            self.general_agent = GeneralAgent()

            # Initialize agents with MCP manager
            await self.entry_agent.initialize(self.mcp_manager)
            await self.specialist_agent.initialize(self.mcp_manager)
            await self.general_agent.initialize(self.mcp_manager)

            # Register agents with A2A service
            if self.a2a_service:
                await self.a2a_service.register_agent(
                    "entry_agent",
                    self.entry_agent.agent,  # Pass the Pydantic AI agent
                )
                await self.a2a_service.register_agent(
                    "specialist_agent",
                    self.specialist_agent.agent,  # Pass the Pydantic AI agent
                )
                await self.a2a_service.register_agent(
                    "general_agent",
                    self.general_agent.agent,  # Pass the Pydantic AI agent
                )

            self.initialized = True
            logger.info("Agent manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize agent manager: {e}")
            raise

    async def receive_a2a_message(
        self,
        recipient: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Receive and dispatch an A2A message to the appropriate agent.

        Args:
            recipient: Target agent name (e.g., 'entry_agent', 'specialist_agent')
            message_type: Message type identifier
            payload: Arbitrary payload for the message

        Returns:
            Response payload as a dictionary

        """
        try:
            if recipient == "entry_agent":
                return await self._handle_entry_agent_message(message_type, payload)
            if recipient == "specialist_agent":
                return await self._handle_specialist_agent_message(
                    message_type,
                    payload,
                )
            if recipient == "general_agent" and self.general_agent:
                # For general agent, no specific message handlers yet
                return {
                    "status": "received",
                    "recipient": recipient,
                    "message_type": message_type,
                }
            return {
                "error": f"Unknown recipient: {recipient}",
                "message_type": message_type,
            }
        except Exception as e:
            logger.error(f"Error handling A2A message for {recipient}: {e}")
            return {"error": str(e)}

    async def shutdown(self) -> None:
        """Shutdown all agents and services."""
        try:
            logger.info("Shutting down agent manager")

            if self.a2a_service:
                await self.a2a_service.stop_server()

            if self.mcp_manager:
                await self.mcp_manager.__aexit__(None, None, None)

            self.initialized = False
            logger.info("Agent manager shut down successfully")

        except Exception as e:
            logger.error(f"Error during agent manager shutdown: {e}")

    async def process_tech_trends_request(
        self,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a tech trends analysis request using the Entry Agent.

        Args:
            request_data: Request data for tech trends analysis

        Returns:
            Tech trends analysis results

        """
        if not self.initialized or not self.entry_agent:
            raise RuntimeError("Agent manager not initialized")

        logger.info("Processing tech trends request")

        try:
            result = await self.entry_agent.process_request(request_data)
            return result
        except Exception as e:
            logger.error(f"Error processing tech trends request: {e}")
            raise

    async def route_user_intent(
        self,
        input_text: str,
        *,
        limit: int = 10,
        include_hn: bool = True,
        include_brave: bool = True,
    ) -> dict[str, Any]:
        """Classify user input and route to trends or general chat.

        Returns dict with keys: route ('trends'|'chat') and data (payload)
        """
        if not self.initialized or not self.entry_agent:
            raise RuntimeError("Agent manager not initialized")

        # 1) First pass through the GeneralAgent
        if not self.general_agent:
            raise RuntimeError("General agent not initialized")
        general_result = await self.general_agent.process_request(
            {
                "message": input_text,
                "limit": limit,
                "include_hn": include_hn,
                "include_brave": include_brave,
            },
        )
        # 2) If handoff requested, send via A2A to EntryAgent
        if general_result.get("handoff"):
            payload = general_result.get("payload", {})
            if self.a2a_service and self.entry_agent:
                # Send an A2A message to entry_agent (simulate request)
                await self.a2a_service.send_message(
                    sender="general_agent",
                    recipient="entry_agent",
                    message_type="tech_trends_request",
                    payload=payload,
                )
            # Still call EntryAgent locally to obtain the result immediately for the HTTP response
            trends_request = {
                "query": payload.get("query", input_text),
                "limit": payload.get("limit", limit),
                "include_hn": payload.get("include_hn", include_hn),
                "include_brave": payload.get("include_brave", include_brave),
            }
            data = await self.entry_agent.process_request(trends_request)
            return {"route": "trends", "data": data}
        # 3) Otherwise, return the GeneralAgent answer
        return {"route": "chat", "data": general_result}

    async def process_repo_intel_request(
        self,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a repository intelligence request using the Specialist Agent.

        Args:
            request_data: Request data for repository analysis

        Returns:
            Repository intelligence results

        """
        if not self.initialized or not self.specialist_agent:
            raise RuntimeError("Agent manager not initialized")

        logger.info("Processing repository intelligence request")

        try:
            result = await self.specialist_agent.process_request(request_data)
            return result
        except Exception as e:
            logger.error(f"Error processing repository intelligence request: {e}")
            raise

    async def process_combined_analysis_request(
        self,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a combined analysis request using both agents.

        Args:
            request_data: Request data for combined analysis

        Returns:
            Combined analysis results

        """
        if not self.initialized or not self.entry_agent or not self.specialist_agent:
            raise RuntimeError("Agent manager not initialized")

        logger.info("Processing combined analysis request")

        try:
            query = request_data.get("query", "")
            auto_detect_repos = request_data.get("auto_detect_repos", True)
            max_repos = request_data.get("max_repos", 5)
            trend_limit = request_data.get("trend_limit", 10)

            # Step 1: Get tech trends from Entry Agent
            trends_request = {
                "query": query,
                "limit": trend_limit,
                "include_hn": True,
                "include_brave": True,
            }

            trends_result = await self.entry_agent.process_request(trends_request)

            # Step 2: Extract repositories or use detected ones
            repositories = []
            if auto_detect_repos and "detected_repositories" in trends_result:
                repositories = trends_result["detected_repositories"][:max_repos]
            else:
                # Fallback to searching for popular repos related to the query
                search_repos_request = {
                    "query": query,
                    "repositories": [],  # Will trigger a search
                    "include_metrics": True,
                }
                # This would ideally use the GitHub search to find relevant repos

            # Step 3: Get repository intelligence from Specialist Agent
            repo_intel_result = {
                "repositories": [],
                "insights": "No repositories found for analysis.",
            }
            if repositories:
                repo_request = {
                    "repositories": repositories,
                    "context": f"Analysis context: {query}",
                    "include_metrics": True,
                    "include_recent_activity": True,
                }

                repo_intel_result = await self.specialist_agent.process_request(
                    repo_request,
                )

            # Step 4: Generate combined analysis
            combined_analysis = await self._generate_combined_analysis(
                trends_result,
                repo_intel_result,
                query,
            )

            return {
                "query": query,
                "trends": trends_result,
                "repositories": repo_intel_result,
                "correlation_analysis": combined_analysis.get(
                    "correlation_analysis",
                    {},
                ),
                "recommendations": combined_analysis.get("recommendations", []),
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing combined analysis request: {e}")
            raise

    async def _generate_combined_analysis(
        self,
        trends_result: dict[str, Any],
        repo_result: dict[str, Any],
        query: str,
    ) -> dict[str, Any]:
        """Generate combined analysis from trends and repository data.

        Args:
            trends_result: Tech trends analysis results
            repo_result: Repository intelligence results
            query: Original query

        Returns:
            Combined analysis with correlations and recommendations

        """
        try:
            # Use Entry Agent to generate combined insights
            analysis_prompt = f"""
            Generate a comprehensive analysis combining tech trends and repository data for query: "{query}" 
            
            Tech Trends Summary:
            {trends_result.get('summary', 'No trends summary available')}
            
            Repository Intelligence:
            {repo_result.get('insights', 'No repository insights available')}
            
            Repositories Analyzed:
            {[repo.get('full_name', 'Unknown') for repo in repo_result.get('repositories', [])]}
            
            Provide:
            1. Correlation analysis between trends and repositories
            2. Key insights about technology adoption
            3. Specific recommendations for developers
            4. Growth opportunities identified
            5. Risk factors to consider
            
            Format as actionable insights for decision-making.
            """

            if self.entry_agent:
                analysis_result = await self.entry_agent.agent.run(analysis_prompt)

                return {
                    "correlation_analysis": repo_result.get("correlation_analysis", {}),
                    "recommendations": [
                        "Explore trending technologies identified in the analysis",
                        "Consider adopting popular frameworks with strong community support",
                        "Monitor repository activity for emerging tools",
                        "Evaluate technology stack alignment with market trends",
                    ],
                    "combined_insights": str(analysis_result),
                }
            return {
                "correlation_analysis": {},
                "recommendations": ["Agent not available for analysis"],
                "combined_insights": "Combined analysis not available",
            }

        except Exception as e:
            logger.error(f"Error generating combined analysis: {e}")
            return {
                "correlation_analysis": {},
                "recommendations": [f"Analysis failed: {e!s}"],
                "combined_insights": "Error occurred during analysis",
            }

    async def _handle_entry_agent_message(
        self,
        message_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle A2A messages for the Entry Agent.

        Args:
            message_type: Type of message
            data: Message data

        Returns:
            Response data

        """
        logger.info(f"Entry Agent received A2A message: {message_type}")

        if message_type == "repo_analysis_response":
            # Handle response from Specialist Agent
            return {
                "status": "acknowledged",
                "timestamp": datetime.utcnow().isoformat(),
            }
        return {"error": f"Unknown message type: {message_type}"}

    async def _handle_specialist_agent_message(
        self,
        message_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle A2A messages for the Specialist Agent.

        Args:
            message_type: Type of message
            data: Message data

        Returns:
            Response data

        """
        logger.info(f"Specialist Agent received A2A message: {message_type}")

        if message_type == "repo_analysis_request" and self.specialist_agent:
            # Handle request from Entry Agent
            try:
                result = await self.specialist_agent.handle_delegation_from_entry(data)
                return result
            except Exception as e:
                logger.error(f"Error handling delegation: {e}")
                return {"error": str(e)}
        else:
            return {"error": f"Unknown message type: {message_type}"}

    async def health_check(self) -> dict[str, Any]:
        """Perform health check for all agents and services.

        Returns:
            Comprehensive health check results

        """
        health_status = {
            "agent_manager": {
                "status": "healthy" if self.initialized else "not_initialized",
                "initialized": self.initialized,
            },
            "agents": {},
            "mcp_servers": {},
            "a2a_service": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Check agent health
        if self.entry_agent:
            health_status["agents"][
                "entry_agent"
            ] = await self.entry_agent.health_check()
        if self.specialist_agent:
            health_status["agents"][
                "specialist_agent"
            ] = await self.specialist_agent.health_check()
        if self.general_agent:
            health_status["agents"][
                "general_agent"
            ] = await self.general_agent.health_check()

        # Check MCP server health
        if self.mcp_manager:
            health_status["mcp_servers"] = await self.mcp_manager.health_check_all()

        # Check A2A service health
        if self.a2a_service:
            health_status["a2a_service"] = await self.a2a_service.health_check()

        return health_status
