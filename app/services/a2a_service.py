"""Agent-to-Agent (A2A) communication service using Pydantic AI's built-in A2A protocol."""

import uuid
from datetime import datetime
from typing import Any

from ..models.schemas import AgentMessage
from ..utils import get_logger, settings

logger = get_logger(__name__)


class A2AService:
    """Service for managing Agent-to-Agent communication using Pydantic AI's A2A protocol."""

    def __init__(self) -> None:
        """Initialize the A2A service."""
        self.agents: dict[str, Any] = {}  # Store Pydantic AI agents
        self.a2a_apps: dict[str, Any] = {}  # Store A2A ASGI applications
        self.message_queue: list[AgentMessage] = []
        self.running = False

    async def start_server(self) -> None:
        """Start the A2A service for inter-agent communication."""
        try:
            self.running = True

            logger.info(
                "A2A service started - agents will be exposed via agent.to_a2a()",
                host=settings.a2a_server_host,
                port=settings.a2a_server_port,
            )

        except Exception as e:
            logger.error(f"Failed to start A2A service: {e}")
            raise

    async def stop_server(self) -> None:
        """Stop the A2A service."""
        if self.running:
            self.running = False
            logger.info("A2A service stopped")

    async def register_agent(self, agent_name: str, agent: Any) -> None:
        """Register a Pydantic AI agent with the A2A service.

        Args:
            agent_name: Name of the agent
            agent: Pydantic AI agent instance

        """
        self.agents[agent_name] = agent

        # Create A2A ASGI app for the agent using Pydantic AI's built-in method
        try:
            # Expose as a proper A2A ASGI application
            self.a2a_apps[agent_name] = agent.to_a2a()
            logger.info(
                f"Agent {agent_name} registered with A2A service and exposed as A2A server",
            )
        except Exception as e:
            # Still register agent but without ASGI exposure if dependencies missing
            logger.warning(f"Failed to create A2A app for {agent_name}: {e}")
            logger.info(f"Agent {agent_name} registered with simplified A2A service")

    async def send_message(
        self,
        sender: str,
        recipient: str,
        message_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> AgentMessage:
        """Send a message from one agent to another.

        Args:
            sender: Name of the sending agent
            recipient: Name of the recipient agent
            message_type: Type of message
            payload: Message payload
            correlation_id: Optional correlation ID for tracking

        Returns:
            The sent message

        Raises:
            ValueError: If sender or recipient not registered

        """
        if sender not in self.agents:
            raise ValueError(f"Sender agent {sender} not registered")

        if recipient not in self.agents:
            raise ValueError(f"Recipient agent {recipient} not registered")

        # Create the message
        message = AgentMessage(
            sender_agent=sender,
            recipient_agent=recipient,
            message_type=message_type,
            payload=payload,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )

        try:
            # Store message in queue for processing
            self.message_queue.append(message)

            # Attempt HTTP-based delivery to FastAPI A2A endpoint, fallback to simulation
            try:
                import httpx

                a2a_url = f"http://localhost:{settings.port}/a2a/send"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        a2a_url,
                        json={
                            "sender": sender,
                            "recipient": recipient,
                            "message_type": message_type,
                            "payload": payload,
                            "correlation_id": message.correlation_id,
                        },
                    )
                    if resp.status_code == 200:
                        logger.info("A2A HTTP message delivered", recipient=recipient)
                    else:
                        logger.warning(
                            "A2A HTTP delivery failed, falling back",
                            status_code=resp.status_code,
                        )
            except Exception as http_err:
                logger.debug(f"A2A HTTP delivery error: {http_err}")

            # Always enqueue locally to reflect message history and support simulation
            recipient_agent = self.agents.get(recipient)
            if recipient_agent:
                logger.info(f"Simulating A2A message delivery to {recipient}")

            logger.info(
                "A2A message sent",
                sender=sender,
                recipient=recipient,
                message_type=message_type,
                correlation_id=message.correlation_id,
            )

            return message

        except Exception as e:
            logger.error(
                "Failed to send A2A message",
                sender=sender,
                recipient=recipient,
                error=str(e),
            )
            raise

    async def broadcast_message(
        self,
        sender: str,
        message_type: str,
        payload: dict[str, Any],
        exclude_agents: list[str] | None = None,
    ) -> list[AgentMessage]:
        """Broadcast a message to all registered agents.

        Args:
            sender: Name of the sending agent
            message_type: Type of message
            payload: Message payload
            exclude_agents: List of agent names to exclude from broadcast

        Returns:
            List of sent messages

        """
        exclude_agents = exclude_agents or [sender]  # Exclude sender by default
        sent_messages = []

        for agent_name in self.agents:
            if agent_name not in exclude_agents:
                try:
                    message = await self.send_message(
                        sender=sender,
                        recipient=agent_name,
                        message_type=message_type,
                        payload=payload,
                    )
                    sent_messages.append(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {agent_name}: {e}")

        logger.info(
            "Message broadcasted",
            sender=sender,
            message_type=message_type,
            recipients=len(sent_messages),
        )

        return sent_messages

    async def get_message_history(
        self,
        agent_name: str,
        limit: int = 100,
    ) -> list[AgentMessage]:
        """Get message history for an agent.

        Args:
            agent_name: Name of the agent
            limit: Maximum number of messages to return

        Returns:
            List of messages

        """
        # This would typically query a message store/database
        # For now, return empty list as placeholder
        logger.info(f"Message history requested for {agent_name}")
        return []

    async def health_check(self) -> dict[str, Any]:
        """Perform health check for the A2A service.

        Returns:
            Health check results

        """
        return {
            "server_running": self.running,
            "registered_agents": list(self.agents.keys()),
            "a2a_apps_created": list(self.a2a_apps.keys()),
            "message_queue_size": len(self.message_queue),
            "server_host": settings.a2a_server_host,
            "server_port": settings.a2a_server_port,
            "timestamp": datetime.utcnow().isoformat(),
        }
