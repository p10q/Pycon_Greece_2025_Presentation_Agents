"""General Agent - Handles non-tech general questions with a friendly tone."""

from datetime import datetime
from typing import Any

from ..utils import get_logger
from .base_agent import BaseAgent

logger = get_logger(__name__)


class GeneralAgent(BaseAgent):
    """Agent dedicated to general Q&A (no MCP usage unless explicitly needed)."""

    def __init__(self) -> None:
        system_prompt = (
            "You are a helpful, concise, and accurate general-purpose assistant. "
            "Answer non-technical questions directly. Do not use external MCP tools."
        )
        super().__init__("general_agent", system_prompt)

    async def process_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Answer a general question.

        Expected request_data: {"message": str}
        """
        message = request_data.get("message", "").strip()
        include_hn = bool(request_data.get("include_hn", True))
        include_brave = bool(request_data.get("include_brave", True))
        limit = int(request_data.get("limit", 10))
        if not message:
            return {
                "response": "Please provide a question.",
                "timestamp": datetime.utcnow().isoformat(),
                "message_type": "error",
            }

        try:
            # Classify first to decide if we should handoff to EntryAgent via A2A
            classification_prompt = (
                "Classify the message strictly as TECH or GENERAL.\n"
                "TECH: programming, software, developer tools, GitHub, frameworks, trends.\n"
                "GENERAL: everything else.\n"
                f"Message: {message}\nRespond with one word: TECH or GENERAL."
            )
            classification_result = await self.agent.run(classification_prompt)
            raw_cls = (
                str(getattr(classification_result, "data", classification_result))
                .strip()
                .upper()
            )
            # Be robust to punctuation or extra words
            import re

            m = re.search(r"\b(TECH|GENERAL)\b", raw_cls)
            cls = m.group(1) if m else "GENERAL"
            # Heuristic boost: treat common tech/trend cues as TECH
            tech_cues = [
                "trend",
                "trends",
                "hn",
                "hacker news",
                "github",
                "repo",
                "repositories",
                "ai",
                "gpt",
                "claude",
                "anthropic",
                "openai",
                "framework",
                "library",
                "model",
                "tech",
                "developer",
                "programming",
            ]
            text_lower = message.lower()
            if cls != "TECH" and any(cue in text_lower for cue in tech_cues):
                cls = "TECH"
            if cls == "TECH":
                # Return a handoff instruction; the manager will send A2A
                return {
                    "handoff": True,
                    "payload": {
                        "query": message,
                        "limit": limit,
                        "include_hn": include_hn,
                        "include_brave": include_brave,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Otherwise answer directly
            result = await self.agent.run(
                f"Provide a helpful, accurate answer to: {message}\nBe concise but informative.",
            )
            return {
                "response": str(result),
                "timestamp": datetime.utcnow().isoformat(),
                "message_type": "general",
            }
        except Exception as e:
            logger.error(f"General agent error: {e}")
            return {
                "response": "I'm sorry, I encountered an error while processing your question.",
                "timestamp": datetime.utcnow().isoformat(),
                "message_type": "error",
            }
