"""Entry Agent (Tech Radar) - Analyzes tech trends using Brave Search and Hacker News."""

import os
import re
from datetime import datetime, timedelta
from typing import Any

from ..services.memory_service import MemoryService, build_default_memory_service
from ..utils import get_logger
from ..utils.config import settings
from ..utils.date_extractor import filter_and_extract_dates
from .base_agent import BaseAgent

logger = get_logger(__name__)

# Environment variable configuration
BRAVE_WEB_SEARCH_LIMIT = int(os.getenv("BRAVE_WEB_SEARCH_LIMIT", "20"))


class EntryAgent(BaseAgent):
    """Entry Agent specializing in tech trend analysis."""

    def __init__(self) -> None:
        """Initialize the Entry Agent."""
        system_prompt = """
        You are an intelligent AI assistant with dual capabilities:
        
        1. TECH RADAR MODE (when queries are about technology, programming, development, GitHub, or trends):
        - Search for latest tech trends using Brave Search
        - Fetch trending stories from Hacker News
        - Analyze and correlate findings across sources
        - Identify emerging technologies and frameworks
        - Detect GitHub repositories mentioned in trends
        - Communicate with the Specialist Agent for repository analysis
        
        When analyzing tech trends:
        - Focus on developer tools, frameworks, programming languages
        - Look for patterns across different sources
        - Identify sentiment and community interest
        - Extract repository names when mentioned
        - Provide clear, actionable insights
        
        2. GENERAL AI MODE (when queries are general questions not related to tech trends):
        - Answer general knowledge questions directly (e.g., "Where is Athens?", "How does photosynthesis work?")
        - Provide helpful information without using MCP tools
        - Be conversational and informative
        - Don't try to search for trends when the question is clearly not tech-related
        
        IMPORTANT: Only use MCP tools (Brave Search, Hacker News, GitHub) when the query is specifically about:
        - Technology trends, frameworks, libraries, tools, AI
        - Programming languages and development
        - GitHub repositories or software projects
        - Developer community discussions
        - Everything related to software, coding, and technology
        
        For general questions like geography, science, history, cooking, etc., provide direct answers without using MCP tools.
        """

        super().__init__("entry_agent", system_prompt)
        # Memory for augmenting queries
        try:
            self.memory: MemoryService = build_default_memory_service()
        except Exception:
            self.memory = None  # type: ignore

    async def process_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Process a tech trends analysis request.

        Args:
            request_data: Request containing query and preferences

        Returns:
            Tech trends analysis results

        """
        query = request_data.get("query", "")
        include_hn = request_data.get("include_hn", True)
        include_brave = request_data.get("include_brave", True)
        limit = request_data.get("limit", 10)

        # Process @file syntax to include file contents
        query = await self._process_file_references(query)

        logger.info(
            "Processing tech trends request",
            query=query,
            include_hn=include_hn,
            include_brave=include_brave,
            limit=limit,
        )

        trends = []
        sources_used = []

        try:
            # Collect results from both sources
            brave_results = []
            hn_results = []

            # Search Brave if enabled
            if include_brave:
                brave_results = await self._search_brave_trends(query, limit)
                sources_used.append("brave_search")

            # Fetch Hacker News if enabled
            if include_hn:
                hn_results = await self._fetch_hacker_news_trends(query, limit)
                sources_used.append("hacker_news")

            # Sort and combine results with proper ordering
            trends = self._combine_and_sort_trends(hn_results, brave_results)

            # Analyze trends using AI
            analysis_prompt = f"""
            Analyze the following tech trends for query: "{query}" 
            
            Trends data: {trends[:20]}  # Limit for token efficiency
            
            Provide:
            1. Summary of key trends
            2. Emerging technologies identified
            3. GitHub repositories mentioned (extract owner/repo format)
            4. Correlation between different sources
            5. Recommendations for further analysis
            
            Focus on actionable insights for developers and technology adoption.
            """

            analysis_result = await self.agent.run(analysis_prompt)

            # Extract GitHub repositories for specialist agent
            repo_extraction_prompt = f"""
            From this analysis, extract GitHub repository names in owner/repo format: 
            
            {analysis_result!s}
            
            Return only a comma-separated list of repository names, e.g.:
            microsoft/vscode, facebook/react, vercel/next.js
            
            If no repositories found, return "none".
            """

            repo_result = await self.agent.run(repo_extraction_prompt)
            detected_repos = []

            repo_result_str = self._extract_content(str(repo_result))
            if repo_result_str and repo_result_str.lower() != "none":
                detected_repos = [
                    repo.strip()
                    for repo in repo_result_str.split(",")
                    if "/" in repo.strip()
                ]

            # Also add trends result to memory for future QA
            try:
                if getattr(self, "memory", None):
                    summary_text = (
                        self._extract_content(str(analysis_result))
                        if "analysis_result" in locals()
                        else ""
                    )
                    trends_text = "\n".join([f"- {t.get('title','')}" for t in trends])
                    combo = f"Query: {query}\nSummary: {summary_text}\nTrends:\n{trends_text}"
                    self.memory.add_interaction(query, combo, kind="trends")
            except Exception:
                pass
            return {
                "query": query,
                "trends": trends,
                "total_items": len(trends),
                "sources": sources_used,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "summary": self._extract_content(str(analysis_result)),
                "detected_repositories": detected_repos,
                "analysis_confidence": self._calculate_confidence(trends, sources_used),
            }

        except Exception as e:
            logger.error(f"Error processing tech trends request: {e}")
            return {
                "error": str(e),
                "query": query,
                "trends": trends,
                "sources": sources_used,
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

    async def classify_query(self, message: str) -> str:
        """Classify a message as TECH or GENERAL.

        Args:
            message: User input

        Returns:
            "TECH" or "GENERAL"

        """
        # Process @file syntax first to provide richer context to classifier
        enriched = await self._process_file_references(message)
        classification_prompt = f"""
            Classify the following message as exactly one of: TECH or GENERAL.
            - TECH: programming, frameworks, developer tools, GitHub, software, technology trends, AI models (e.g., Claude, GPT), HN topics.
            - GENERAL: geography, history, cooking, casual chit-chat, everyday facts.

            Message: "{enriched}"

            Respond with only one token: TECH or GENERAL.
            """
        try:
            classification_result = await self.agent.run(classification_prompt)
            result_content = self._extract_content(str(classification_result))
            result = result_content.strip().upper()
            return "TECH" if result == "TECH" else "GENERAL"
        except Exception as e:
            logger.error(f"Classification failed, defaulting to GENERAL: {e}")
            return "GENERAL"

    async def _search_brave_trends(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search for trends using direct web search - DYNAMIC ONLY.

        Args:
            query: Search query (may include file content)
            limit: Maximum number of results

        Returns:
            List of trend items from web search

        """
        try:
            # Extract meaningful search terms from the query, including file content
            search_terms = self._extract_dynamic_search_terms(query)

            # Use Brave Search MCP server for web search
            # Use configured web search limit from environment
            web_limit = settings.web_search_limit
            logger.info(
                f"Performing Brave Search via MCP - fetching {web_limit} results",
            )
            return await self._fetch_brave_search_mcp(search_terms, web_limit)

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def _fetch_hacker_news_trends(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch trending stories from Hacker News using the MCP server.

        Args:
            query: Query context for filtering (may include file content)
            limit: Maximum number of stories (will use 50-100 for better coverage)

        Returns:
            List of trend items from Hacker News

        """
        try:
            # Use configured HN stories limit from environment
            search_limit = settings.hn_stories_limit

            # Extract search context from query for filtering
            search_context = self._extract_dynamic_search_terms(query)

            # Ensure MCP manager and HN client are available
            if not self.mcp_manager:
                logger.warning("MCP manager not initialized; skipping HN fetch")
                return []

            hn_client = self.mcp_manager.get_client("hacker_news")
            if not hn_client:
                logger.warning(
                    "Hacker News MCP client not available; skipping HN fetch",
                )
                return []

            # Prefer searching stories by query for higher relevance
            logger.info("Fetching HN stories via MCP: search_stories")
            mcp_result = await hn_client.call_tool(
                "search_stories",
                {
                    "query": search_context,
                    "limit": min(search_limit, max(limit * 3, limit)),
                },
            )

            # Normalize MCP result shape
            stories_payload: list[dict[str, Any]] = []
            if isinstance(mcp_result, dict) and "result" in mcp_result:
                result_data = mcp_result["result"]
                # Check if result_data has a "stories" key
                if isinstance(result_data, dict) and "stories" in result_data:
                    stories_payload = result_data["stories"] or []
                else:
                    stories_payload = result_data if isinstance(result_data, list) else []
            elif isinstance(mcp_result, list):
                stories_payload = mcp_result
            else:
                logger.warning(f"Unexpected HN MCP response format: {type(mcp_result)}")
                return []

            # Filter and convert to Trend items (looser matching for better recall)
            trends: list[dict[str, Any]] = []
            for story in stories_payload:
                if self._is_story_relevant(
                    story,
                    search_context,
                    allow_plural=True,
                    allow_substring=True,
                ):
                    trend_item = self._convert_hn_story_to_trend(story)
                    if trend_item:
                        trends.append(trend_item)
                        if len(trends) >= limit:
                            break

            logger.info(f"Found {len(trends)} relevant HN stories via MCP")
            # If not enough results, fallback to topstories and fill up
            if len(trends) < limit:
                try:
                    logger.info("HN MCP fallback: fetching topstories to fill results")
                    top_res = await hn_client.call_tool(
                        "get_stories",
                        {"story_type": "topstories", "limit": search_limit},
                    )
                    top_payload: list[dict[str, Any]] = []
                    if isinstance(top_res, dict) and "result" in top_res:
                        result_data = top_res["result"]
                        # Check if result_data has a "stories" key
                        if isinstance(result_data, dict) and "stories" in result_data:
                            top_payload = result_data["stories"] or []
                        else:
                            top_payload = result_data if isinstance(result_data, list) else []
                    elif isinstance(top_res, list):
                        top_payload = top_res
                    for story in top_payload:
                        trend_item = self._convert_hn_story_to_trend(story)
                        if trend_item:
                            # If we have search context, ensure minimal relevance using tags/keywords
                            if not search_context or self._has_minimal_relevance(
                                trend_item["title"],
                                search_context,
                            ):
                                trends.append(trend_item)
                                if len(trends) >= limit:
                                    break
                    logger.info(f"HN fallback filled to {len(trends)} items")
                except Exception as fill_err:
                    logger.debug(f"HN fallback fill failed: {fill_err}")
            return trends[:limit]

        except Exception as e:
            logger.error(f"Hacker News MCP fetch failed: {e}")
            return []

    async def _parse_hn_mcp_response(
        self,
        result: Any,
        search_context: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Parse actual Hacker News MCP server response dynamically.

        Args:
            result: MCP server response
            search_context: Search context extracted from query
            limit: Maximum number of items to return

        Returns:
            List of parsed HN trend items filtered by relevance

        """
        trends = []

        try:
            # Convert result to string and try to extract structured data
            result_str = str(result)
            logger.info(f"Parsing dynamic HN MCP data with context: {search_context}")

            # Try to parse JSON-like structures in the response
            import json
            import re

            # Look for JSON arrays or objects in the response
            json_pattern = r"\[.*?\]|\{.*?\}"
            json_matches = re.findall(json_pattern, result_str, re.DOTALL)

            for match in json_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        # Process list of stories
                        for story in data[: limit * 2]:  # Get more to filter
                            if self._is_story_relevant(story, search_context):
                                trend_item = self._convert_hn_story_to_trend(story)
                                if trend_item:
                                    trends.append(trend_item)
                                    if len(trends) >= limit:
                                        break
                    elif isinstance(data, dict) and "stories" in data:
                        # Process stories from dict structure
                        for story in data["stories"][: limit * 2]:
                            if self._is_story_relevant(story, search_context):
                                trend_item = self._convert_hn_story_to_trend(story)
                                if trend_item:
                                    trends.append(trend_item)
                                    if len(trends) >= limit:
                                        break
                except json.JSONDecodeError:
                    continue

            # If no structured data found, try to extract story info from text
            if not trends:
                trends = self._extract_stories_from_text(
                    result_str,
                    search_context,
                    limit,
                )

            logger.info(
                f"Extracted {len(trends)} relevant HN stories from MCP response",
            )
            return trends

        except Exception as e:
            logger.error(f"Failed to parse HN MCP response dynamically: {e}")
            return []

    def _create_realistic_hn_fallback_data_DEPRECATED(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Create realistic-looking Hacker News fallback data with proper URLs.

        Args:
            query: Search query for context
            limit: Maximum number of items

        Returns:
            List of realistic HN trend items

        """
        # Create realistic HN articles that might be trending
        realistic_hn_articles = [
            {
                "title": "Vanishing from Hyundai's data network",
                "url": "https://news.ycombinator.com/item?id=42645123",
                "external_url": "https://example.com/hyundai-data-breach",
                "score": 285,
                "author": "techuser123",
                "comments": 127,
                "story_type": "story",
            },
            {
                "title": f"Show HN: I built a {query} monitoring tool",
                "url": "https://news.ycombinator.com/item?id=42644987",
                "external_url": None,  # Show HN posts often don't have external URLs
                "score": 156,
                "author": "developer_hn",
                "comments": 73,
                "story_type": "show_hn",
            },
            {
                "title": f"Ask HN: Best practices for {query} in 2024?",
                "url": "https://news.ycombinator.com/item?id=42644821",
                "external_url": None,  # Ask HN posts don't have external URLs
                "score": 89,
                "author": "curious_dev",
                "comments": 45,
                "story_type": "ask_hn",
            },
            {
                "title": f"New {query} framework promises 10x performance",
                "url": "https://news.ycombinator.com/item?id=42644756",
                "external_url": f"https://tech-blog.example.com/{query.replace(' ', '-')}-framework",
                "score": 234,
                "author": "framework_creator",
                "comments": 98,
                "story_type": "story",
            },
            {
                "title": f"Why {query} is becoming the new standard",
                "url": "https://news.ycombinator.com/item?id=42644652",
                "external_url": f"https://medium.com/@techwriter/{query.replace(' ', '-')}-new-standard",
                "score": 167,
                "author": "industry_expert",
                "comments": 82,
                "story_type": "story",
            },
        ]

        trends = []
        for i, article in enumerate(realistic_hn_articles[:limit]):
            # Filter for relevance to query
            if self._is_relevant_to_query(article["title"].lower(), query):
                trend = {
                    "title": article["title"],
                    "url": article["url"],  # Always use HN discussion URL
                    "source": "hacker_news",
                    "score": article["score"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "description": self._generate_hn_description(
                        article["title"],
                        article["story_type"],
                    ),
                    "tags": self._extract_tech_tags(article["title"]),
                    "metadata": {
                        "hn_id": (
                            int(article["url"].split("id=")[1])
                            if "id=" in article["url"]
                            else 42644000 + i
                        ),
                        "author": article["author"],
                        "comments": article["comments"],
                        "story_type": article["story_type"],
                        "external_url": article.get(
                            "external_url",
                        ),  # Original article URL if available
                        "fallback": True,
                    },
                }
                trends.append(trend)

        # If no relevant articles found, create a generic search result
        if not trends:
            trend = {
                "title": f"HN Search: {query}",
                "url": f"https://news.ycombinator.com/search?q={query.replace(' ', '+')}",
                "source": "hacker_news",
                "score": 95,
                "timestamp": datetime.utcnow().isoformat(),
                "description": f"Search results for '{query}' on Hacker News",
                "tags": self._extract_tech_tags(query),
                "metadata": {
                    "hn_id": 42644000,
                    "author": "hn_search",
                    "comments": 0,
                    "story_type": "search",
                    "fallback": True,
                },
            }
            trends.append(trend)

        return trends

    def _generate_hn_description(self, title: str, story_type: str) -> str:
        """Generate appropriate description for HN story based on type.

        Args:
            title: Story title
            story_type: Type of HN story

        Returns:
            Generated description

        """
        if story_type == "ask_hn":
            return f"Community discussion asking about: {title}"
        if story_type == "show_hn":
            return f"Community showcase: {title}"
        return f"Hacker News discussion: {title}"

    def _extract_tech_tags(self, text: str) -> list[str]:
        """Extract technology tags from text.

        Args:
            text: Text to analyze

        Returns:
            List of technology tags

        """
        tech_keywords = [
            "python",
            "javascript",
            "typescript",
            "react",
            "vue",
            "angular",
            "node",
            "express",
            "fastapi",
            "django",
            "flask",
            "nextjs",
            "docker",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "terraform",
            "ai",
            "ml",
            "machine learning",
            "llm",
            "gpt",
            "neural",
            "framework",
            "library",
            "tool",
            "api",
            "database",
            "sql",
            "git",
            "github",
            "ci/cd",
            "devops",
            "microservices",
        ]

        text_lower = text.lower()
        found_tags = []

        for keyword in tech_keywords:
            if keyword in text_lower:
                found_tags.append(keyword)

        return found_tags

    def _is_relevant_to_query(self, title: str, query: str) -> bool:
        """Check if a title is relevant to the search query.

        Args:
            title: Title to check
            query: Search query

        Returns:
            True if relevant, False otherwise

        """
        query_words = query.lower().split()
        title_lower = title.lower()

        # Check if any query words are in the title
        for word in query_words:
            if len(word) > 2 and word in title_lower:
                return True

        # Check for general tech relevance
        tech_indicators = [
            "framework",
            "library",
            "tool",
            "api",
            "code",
            "dev",
            "programming",
        ]
        for indicator in tech_indicators:
            if indicator in title_lower:
                return True

        return False

    async def _process_file_references(self, query: str) -> str:
        """Process @file references in the query and replace them with file contents.

        Args:
            query: Query string that may contain @filename references

        Returns:
            Query string with file contents injected

        """
        import os
        import re
        from pathlib import Path

        # Find all @filename patterns
        file_pattern = r"@([a-zA-Z0-9_.-]+\.json)"
        matches = re.findall(file_pattern, query)

        if not matches:
            return query

        logger.info(f"Found file references: {matches}")

        # Process each file reference
        for filename in matches:
            try:
                file_content = None

                # First, try to find the file dynamically in the data directory
                data_dir = Path("data")
                if data_dir.exists():
                    # Search for the file in all subdirectories
                    for json_file in data_dir.rglob(filename):
                        try:
                            with open(json_file, encoding="utf-8") as f:
                                file_content = f.read()
                            logger.info(f"Found and read {filename} from {json_file}")
                            break
                        except Exception as read_error:
                            logger.warning(f"Failed to read {json_file}: {read_error}")
                            continue

                # If not found dynamically, try MCP filesystem client
                if not file_content and self.mcp_manager:
                    client = self.mcp_manager.get_client("filesystem")
                    if client:
                        # Try common paths
                        possible_paths = [
                            f"/app/data/config/{filename}",
                            f"/app/data/examples/{filename}",
                            f"/app/data/{filename}",
                        ]

                        for file_path in possible_paths:
                            try:
                                result = await client.call_tool(
                                    "read_file",
                                    {"path": file_path},
                                )
                                if "content" in result:
                                    file_content = result["content"]
                                    logger.info(
                                        f"Read {filename} via MCP from {file_path}",
                                    )
                                    break
                                if "error" not in result:
                                    file_content = str(result)
                                    logger.info(
                                        f"Read {filename} via MCP from {file_path}",
                                    )
                                    break
                            except Exception as e:
                                logger.debug(f"MCP read failed for {file_path}: {e}")
                                continue

                # If still not found, try legacy hardcoded paths as final fallback
                if not file_content:
                    legacy_paths = [
                        f"data/config/{filename}",
                        f"data/examples/{filename}",
                        f"data/{filename}",
                    ]

                    for local_path in legacy_paths:
                        if os.path.exists(local_path):
                            try:
                                with open(local_path, encoding="utf-8") as f:
                                    file_content = f.read()
                                logger.info(
                                    f"Read {filename} from legacy path {local_path}",
                                )
                                break
                            except Exception as e:
                                logger.warning(f"Failed to read {local_path}: {e}")
                                continue

                if not file_content:
                    logger.warning(f"File {filename} not found in any location")
                    # Replace with a helpful message instead of removing
                    query = query.replace(
                        f"@{filename}",
                        f"[File {filename} not found - please check the file exists in the /data folder]",
                    )
                    continue

                # Replace @filename with file contents in a formatted way
                replacement = f"\n\n--- Content of {filename} ---\n{file_content}\n--- End of {filename} ---\n\n"
                query = query.replace(f"@{filename}", replacement)

                logger.info(f"Successfully injected content from {filename}")

            except Exception as e:
                logger.error(f"Failed to process file reference {filename}: {e}")
                # Replace with error message instead of removing
                query = query.replace(
                    f"@{filename}",
                    f"[Error reading {filename}: {e!s}]",
                )

        return query

    def _calculate_confidence(
        self,
        trends: list[dict[str, Any]],
        sources: list[str],
    ) -> float:
        """Calculate confidence score for the analysis.

        Args:
            trends: List of trend items
            sources: List of sources used

        Returns:
            Confidence score between 0.0 and 1.0

        """
        base_confidence = 0.5

        # Increase confidence based on number of trends
        trend_factor = min(len(trends) / 20, 0.3)

        # Increase confidence based on number of sources
        source_factor = len(sources) * 0.1

        # Increase confidence based on data quality
        quality_factor = 0.0
        if trends:
            avg_score = sum(t.get("score", 0) for t in trends) / len(trends)
            quality_factor = min(avg_score / 100, 0.2)

        return min(base_confidence + trend_factor + source_factor + quality_factor, 1.0)

    async def delegate_to_specialist(
        self,
        repositories: list[str],
        context: str,
    ) -> dict[str, Any]:
        """Delegate repository analysis to the Specialist Agent.

        Args:
            repositories: List of repository names to analyze
            context: Context for the analysis

        Returns:
            Message to send to Specialist Agent

        """
        message = await self.send_message_to_agent(
            recipient="specialist_agent",
            message_type="repo_analysis_request",
            payload={
                "repositories": repositories,
                "context": context,
                "requested_by": "entry_agent",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            "Delegated repository analysis to Specialist Agent",
            repositories=repositories,
            context=context[:100] + "..." if len(context) > 100 else context,
        )

        return message.dict()

    async def process_general_chat(self, message: str) -> dict[str, Any]:
        """Process a general chat message (non-tech specific).

        Args:
            message: User's general question or message

        Returns:
            AI response to the general question

        """
        logger.info(f"Processing general chat message: {message[:100]}...")

        # Process @file syntax to include file contents
        message = await self._process_file_references(message)

        try:
            # Classify intent using shared classifier
            classification = await self.classify_query(message)
            is_tech_query = classification == "TECH"

            if is_tech_query:
                # This is actually a tech query, suggest using the trends search instead
                response = f"""This seems like a technology-related question! For the best results, I recommend using the "Analyze Trends" feature above, which will search through Hacker News, GitHub, and the web for up-to-date information about: {message}
                
However, I can still provide a general answer: Let me give you some basic information about your question."""

                # Still provide a basic answer
                general_prompt = f"""
                Provide a helpful, informative answer to this question: {message}
                
                Keep it concise but informative. If it's about technology, mention that more detailed and current information could be found through tech trend analysis.
                """

                general_result = await self.agent.run(general_prompt)
                response += f"\n\n{self._extract_content(str(general_result))}"

            else:
                # This is a general question, answer directly
                general_prompt = f"""
                You are a helpful AI assistant. Answer this question clearly and informatively: {message}
                
                Provide accurate, helpful information. Be conversational and friendly.
                """

                # Retrieve relevant memories and augment prompt
                context_block = ""
                if getattr(self, "memory", None):
                    memories = self.memory.search_memories(message, k=5)
                    if memories:
                        joined = "\n\n".join([m.get("text", "") for m in memories])
                        context_block = f"\n\nRelevant past interactions (for continuity):\n{joined}\n\n"
                result = await self.agent.run(general_prompt + context_block)
                response = self._extract_content(str(result))

            # Store to memory (best-effort)
            try:
                if getattr(self, "memory", None):
                    self.memory.add_interaction(message, response, kind="chat")
            except Exception:
                pass
            return {
                "response": response,
                "timestamp": datetime.utcnow().isoformat(),
                "message_type": "tech_suggestion" if is_tech_query else "general",
            }

        except Exception as e:
            logger.error(f"Error processing general chat: {e}")
            return {
                "response": "I'm sorry, I encountered an error while processing your question. Please try again.",
                "timestamp": datetime.utcnow().isoformat(),
                "message_type": "error",
            }

    def _extract_content(self, agent_result_str: str) -> str:
        """Extract clean content from agent result string.

        Args:
            agent_result_str: String representation of agent result

        Returns:
            Clean content without wrapper text

        """
        # Remove AgentRunResult wrapper if present
        if "AgentRunResult(output=" in agent_result_str:
            # Extract content between quotes
            start = agent_result_str.find("output='") + 8
            if start > 7:  # Found the pattern
                end = agent_result_str.rfind("')")
                if end > start:
                    content = agent_result_str[start:end]
                    # Unescape quotes
                    content = content.replace("\\'", "'").replace('\\"', '"')
                    return content

            # Try alternative pattern with double quotes
            start = agent_result_str.find('output="') + 8
            if start > 7:
                end = agent_result_str.rfind('")')
                if end > start:
                    content = agent_result_str[start:end]
                    # Unescape quotes
                    content = content.replace('\\"', '"').replace("\\'", "'")
                    return content

        # If no wrapper found, return as-is
        return agent_result_str

    def _extract_dynamic_search_terms(self, query: str) -> str:
        """Extract meaningful search terms from query including file content.

        Args:
            query: Full query which may include file content

        Returns:
            Cleaned search terms for API calls (focused on technical terms)

        """
        import re

        # Remove file content markers
        clean_query = re.sub(
            r"--- Content of.*?--- End of.*?---",
            "",
            query,
            flags=re.DOTALL,
        )
        clean_query = re.sub(
            r"--- Content of.*?---.*?--- End of.*?---",
            "",
            clean_query,
            flags=re.DOTALL,
        )

        # Extract meaningful terms from file content if present
        file_terms = []
        file_content_pattern = r"--- Content of.*?---\s*(.*?)\s*--- End of.*?---"
        file_matches = re.findall(file_content_pattern, query, re.DOTALL)

        for file_content in file_matches:
            # Extract key terms from JSON content
            if '"Context"' in file_content or '"Tools"' in file_content:
                # Extract from JSON structure
                context_match = re.search(r'"Context":\s*"([^"]*)"', file_content)
                if context_match:
                    file_terms.append(context_match.group(1))

                # Extract tool names
                tool_matches = re.findall(r'"Name":\s*"([^"]*)"', file_content)
                file_terms.extend(tool_matches)
            else:
                # Extract general meaningful words
                words = re.findall(r"\b[a-zA-Z]{3,}\b", file_content)
                file_terms.extend(words[:5])  # Take first 5 meaningful words

        # Extract core technical terms from the clean query, ignoring common words
        core_terms = []
        if clean_query.strip():
            # Remove punctuation and split into words
            clean_context = re.sub(r"[^\w\s]", " ", clean_query.lower())

            for term in clean_context.split():
                # Focus on technical terms and important keywords
                if (
                    len(term) >= 3
                    and term
                    not in [
                        "tell",
                        "me",
                        "the",
                        "and",
                        "for",
                        "you",
                        "about",
                        "could",
                        "find",
                        "anything",
                        "related",
                        "everything",
                        "news",
                        "most",
                        "trendy",
                        "currently",
                        "like",
                        "tools",
                        "interested",
                        "concept",
                        "things",
                        "trends",
                        "what",
                        "how",
                        "why",
                        "when",
                        "where",
                        "which",
                        "who",
                    ]
                ) or term in [
                    "ai",
                    "ml",
                    "api",
                    "cpu",
                    "gpu",
                    "sql",
                    "css",
                    "js",
                    "go",
                    "c++",
                    "rust",
                    "java",
                    "python",
                ]:
                    core_terms.append(term)

        # Combine core terms with file terms
        all_terms = []
        if core_terms:
            all_terms.extend(core_terms)
        if file_terms:
            all_terms.extend(file_terms)

        # If no core terms found, use the original query but log a warning
        if not all_terms and clean_query.strip():
            logger.warning(
                f"No core technical terms extracted from query: {clean_query}",
            )
            return clean_query.strip()

        result = " ".join(all_terms)
        logger.info(f"Extracted search terms: '{result}' from query: '{query[:50]}...'")
        return result

    def _is_story_relevant(
        self,
        story: dict,
        search_context: str,
        allow_plural: bool = False,
        allow_substring: bool = False,
    ) -> bool:
        """Check if a HN story is relevant to the search context - STRICT MATCHING.

        Args:
            story: HN story dict with title, url, etc.
            search_context: Search terms to match against

        Returns:
            True if story is relevant (STRICT: must contain exact search terms)

        """
        if not search_context or not story:
            return False  # No context = no relevance

        # Extract searchable text from story (guard against None)
        searchable_text = ""
        if isinstance(story, dict):
            title_val = story.get("title") or ""
            text_val = story.get("text") or ""
            url_val = story.get("url") or ""
            searchable_text += title_val + " "
            searchable_text += text_val + " "
            searchable_text += url_val + " "

        searchable_text = searchable_text.lower().strip()

        if not searchable_text:
            return False  # No content to search

        # Extract core search terms (technical terms, not common words)
        import re

        search_terms = []

        # Clean the search context first - remove punctuation
        clean_context = re.sub(r"[^\w\s]", " ", search_context.lower())

        for term in clean_context.split():
            # Include technical terms (5+ chars) and exclude common words
            if (
                len(term) >= 5
                and term
                not in [
                    "tell",
                    "the",
                    "and",
                    "for",
                    "you",
                    "about",
                    "could",
                    "find",
                    "anything",
                    "related",
                    "everything",
                    "news",
                    "most",
                    "trendy",
                    "currently",
                    "like",
                    "tools",
                    "interested",
                    "concept",
                    "things",
                ]
            ) or term in [
                "ai",
                "ml",
                "api",
                "cpu",
                "gpu",
                "sql",
                "css",
                "js",
                "go",
                "c++",
                "rust",
                "java",
                "python",
            ]:
                search_terms.append(term)

        if not search_terms:
            return False  # If no meaningful search terms, no relevance

        logger.debug(
            f"Checking story '{story.get('title', '')}' against STRICT terms: {search_terms}",
        )

        # STRICT MATCHING: Story must contain at least one exact search term
        tokens = re.findall(r"\b\w+\b", searchable_text.lower())
        token_set = set(tokens)
        for term in search_terms:
            # Exact token match
            if term in token_set:
                logger.info(
                    f"Story EXACTLY matches term '{term}': {story.get('title', '')}",
                )
                return True
            # Allow simple plural/singular variants
            if allow_plural:
                if term.endswith("s") and term[:-1] in token_set:
                    return True
                if (
                    (term + "s") in token_set
                    or (term + "es") in token_set
                    or term.rstrip("s") in token_set
                ):
                    return True
            # Allow substring fallback (e.g., 'agent' in 'agents')
            if allow_substring and term in searchable_text:
                return True

        logger.debug(f"Story rejected - no exact matches: {story.get('title', '')}")
        return False

    def _has_minimal_relevance(self, title: str, search_context: str) -> bool:
        """Loose relevance check used for topstories fallback.
        Accept if any search term (>=4 chars) is a substring of the title.
        """
        if not search_context:
            return True
        title_lower = (title or "").lower()
        clean_context = re.sub(r"[^\w\s]", " ", search_context.lower())
        for term in clean_context.split():
            if len(term) >= 4 and term not in ["trends", "about", "news", "tools"]:
                if term in title_lower or (
                    term.endswith("s") and term[:-1] in title_lower
                ):
                    return True
        return False

    def _convert_hn_story_to_trend(self, story: dict) -> dict:
        """Convert HN story dict to trend item format.

        Args:
            story: HN story from MCP response

        Returns:
            Formatted trend item or None if too old

        """
        try:
            story_id = story.get("id", 0)
            title = story.get("title") or "Untitled Story"
            score = story.get("score") or 0

            # Extract and validate timestamp (filter stories older than 2 months)
            story_time = story.get("time")
            if story_time:
                story_date = datetime.fromtimestamp(story_time)
                two_months_ago = datetime.now() - timedelta(days=60)

                # Skip stories older than 2 months
                if story_date < two_months_ago:
                    return None

                timestamp = story_date.isoformat()
            else:
                # Skip stories without timestamps
                return None

            # Generate HN URL
            hn_url = (
                f"https://news.ycombinator.com/item?id={story_id}" if story_id else None
            )

            # Use external URL if available, otherwise HN discussion
            external_url = story.get("url") or None
            final_url = external_url if external_url else hn_url

            # Calculate weighted score for HN: 0.5 points + 0.4 relevance + 0.1 recency
            weighted_score = self._calculate_hn_weighted_score(score, story_date, title)

            return {
                "title": title,
                "url": final_url,
                "source": "hacker_news",
                "score": weighted_score,
                "timestamp": timestamp,
                "description": f"HN Story: {title}",
                "tags": self._extract_tech_tags(title),
                "metadata": {
                    "hn_id": story_id,
                    "hn_score": score,
                    "hn_points": score,  # Store original points for UI display
                    "comments": story.get("descendants", 0),
                    "author": story.get("by", "unknown"),
                    "hn_url": hn_url,
                    "external_url": external_url,
                },
            }
        except Exception as e:
            logger.warning(f"Failed to convert HN story to trend: {e}")
            return None

    def _extract_stories_from_text(
        self,
        text: str,
        search_context: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Extract story information from text response.

        Args:
            text: Raw text response
            search_context: Search context for filtering
            limit: Maximum stories to extract

        Returns:
            List of extracted trend items

        """
        trends = []
        import re

        # Look for story patterns in text
        # Pattern for "Title (score points)" or similar
        story_patterns = [
            r"(\d+)\.\s*([^(]+)\s*\((\d+)\s*points?\)",  # "1. Title (123 points)"
            r"([^:]+):\s*(\d+)\s*points",  # "Title: 123 points"
            r"([^-]+)\s*-\s*(\d+)\s*points",  # "Title - 123 points"
        ]

        story_id = 42000000  # Start with a realistic HN ID

        for pattern in story_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches[:limit]:
                if len(match) >= 2:
                    if len(match) == 3:  # Pattern with number, title, score
                        _, title, score = match
                    else:  # Pattern with title, score
                        title, score = match

                    title = title.strip()
                    try:
                        score = int(score)
                    except:
                        score = 50  # Default score

                    # Check relevance
                    if search_context and not any(
                        term.lower() in title.lower()
                        for term in search_context.split()
                        if len(term) > 2
                    ):
                        continue

                    trend_item = {
                        "title": title,
                        "url": f"https://news.ycombinator.com/item?id={story_id}",
                        "source": "hacker_news",
                        "score": min(100, max(1, score)),
                        "timestamp": datetime.utcnow().isoformat(),
                        "description": f"HN Story: {title}",
                        "tags": self._extract_tech_tags(title),
                        "metadata": {
                            "hn_id": story_id,
                            "hn_score": score,
                            "extracted_from_text": True,
                        },
                    }

                    trends.append(trend_item)
                    story_id += 1

                    if len(trends) >= limit:
                        break

            if trends:
                break  # Found stories with this pattern

        return trends

    async def _parse_brave_mcp_response(
        self,
        result: Any,
        search_terms: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Parse actual Brave Search MCP server response dynamically.

        Args:
            result: MCP server response
            search_terms: Search terms used
            limit: Maximum number of items to return

        Returns:
            List of parsed Brave search trend items

        """
        trends = []

        try:
            result_str = str(result)
            logger.info(f"Parsing dynamic Brave Search MCP data for: {search_terms}")

            import json
            import re

            # Try to parse JSON structures in the response
            json_pattern = r"\[.*?\]|\{.*?\}"
            json_matches = re.findall(json_pattern, result_str, re.DOTALL)

            for match in json_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        # Process list of search results
                        for item in data[:limit]:
                            trend_item = await self._convert_brave_result_to_trend(
                                item,
                                search_terms,
                            )
                            if trend_item:
                                trends.append(trend_item)
                    elif isinstance(data, dict) and "results" in data:
                        # Process results from dict structure
                        for item in data["results"][:limit]:
                            trend_item = await self._convert_brave_result_to_trend(
                                item,
                                search_terms,
                            )
                            if trend_item:
                                trends.append(trend_item)
                except json.JSONDecodeError:
                    continue

            # If no structured data found, try to extract from text
            if not trends:
                trends = self._extract_search_results_from_text(
                    result_str,
                    search_terms,
                    limit,
                )

            logger.info(
                f"Extracted {len(trends)} relevant search results from Brave MCP response",
            )
            return trends

        except Exception as e:
            logger.error(f"Failed to parse Brave MCP response dynamically: {e}")
            return []

    async def _convert_brave_result_to_trend(
        self,
        result: dict,
        search_terms: str,
    ) -> dict:
        """Convert Brave search result to trend item format.

        Args:
            result: Search result from Brave MCP response
            search_terms: Original search terms

        Returns:
            Formatted trend item

        """
        try:
            title = result.get("title", "Untitled Result")
            url = result.get("url", result.get("link", ""))
            description = result.get("description", result.get("snippet", ""))

            # Calculate relevance score based on title and description match
            score = self._calculate_search_relevance(
                title + " " + description,
                search_terms,
            )

            return {
                "title": title,
                "url": url,
                "source": "brave_search",
                "score": score,
                "timestamp": datetime.utcnow().isoformat(),  # Will be processed by date extractor
                "description": description,
                "tags": self._extract_tech_tags(title + " " + description),
                "metadata": {
                    "search_terms": search_terms,
                    "rank": result.get("rank", 0),
                },
            }
        except Exception as e:
            logger.warning(f"Failed to convert Brave result to trend: {e}")
            return None

    def _extract_search_results_from_text(
        self,
        text: str,
        search_terms: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Extract search results from text response.

        Args:
            text: Raw text response
            search_terms: Search terms for context
            limit: Maximum results to extract

        Returns:
            List of extracted trend items

        """
        trends = []
        import re

        # Look for URL patterns and titles
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
        urls = re.findall(url_pattern, text)

        # Look for title patterns near URLs
        lines = text.split("\n")

        for i, line in enumerate(lines[: limit * 2]):
            line = line.strip()
            if not line:
                continue

            # Look for URLs in this line or nearby lines
            line_urls = re.findall(url_pattern, line)

            if line_urls:
                url = line_urls[0]
                # Use the line as title, cleaning it up
                title = re.sub(url_pattern, "", line).strip()
                title = re.sub(r"[^\w\s-]", " ", title).strip()

                if not title:
                    title = f"Search result for {search_terms}"

                score = self._calculate_search_relevance(title, search_terms)

                trend_item = {
                    "title": title,
                    "url": url,
                    "source": "brave_search",
                    "score": score,
                    "timestamp": datetime.utcnow().isoformat(),  # Will be processed by date extractor
                    "description": f"Search result for: {search_terms}",
                    "tags": self._extract_tech_tags(title),
                    "metadata": {
                        "search_terms": search_terms,
                        "extracted_from_text": True,
                    },
                }

                trends.append(trend_item)

                if len(trends) >= limit:
                    break

        return trends

    def _calculate_search_relevance(self, text: str, search_terms: str) -> int:
        """Calculate relevance score for search result.

        Args:
            text: Text to analyze
            search_terms: Search terms to match

        Returns:
            Relevance score (1-100)

        """
        if not text or not search_terms:
            return 50

        text_lower = text.lower()
        terms = search_terms.lower().split()

        score = 30  # Base score

        for term in terms:
            if len(term) > 2:
                # Exact match gets high score
                if term in text_lower:
                    score += 20
                # Partial match gets medium score
                elif any(term in word for word in text_lower.split()):
                    score += 10

        return min(100, max(1, score))

    def _calculate_hn_weighted_score(
        self,
        hn_points: int,
        story_date: datetime,
        title: str,
    ) -> int:
        """Calculate weighted score for HN stories: 0.5 points + 0.4 relevance + 0.1 recency.

        Args:
            hn_points: Original HN points/score
            story_date: Publication date of the story
            title: Story title for relevance calculation

        Returns:
            Weighted score (1-100)

        """
        try:
            # Normalize HN points (0-100 scale, most stories are 0-500 points)
            points_score = min(
                100,
                (hn_points / 5),
            )  # Divide by 5 to normalize 500->100

            # Calculate relevance score based on title (0-100 scale)
            relevance_score = min(
                100,
                len([word for word in title.lower().split() if len(word) > 3]) * 10,
            )

            # Calculate recency score (0-100 scale, newer = higher)
            now = datetime.now()
            hours_ago = (now - story_date).total_seconds() / 3600
            recency_score = max(
                0,
                100 - (hours_ago / 24 * 10),
            )  # Lose 10 points per day

            # Weighted combination: 0.5 points + 0.4 relevance + 0.1 recency
            weighted_score = (
                points_score * 0.5 + relevance_score * 0.4 + recency_score * 0.1
            )

            return int(min(100, max(1, weighted_score)))

        except Exception as e:
            logger.debug(f"Failed to calculate weighted score: {e}")
            return min(100, max(1, hn_points))

    async def _fetch_hn_direct_api(
        self,
        search_context: str,
        search_limit: int,
        final_limit: int,
    ) -> list[dict[str, Any]]:
        """Deprecated: Direct HN API fetch is disabled; using MCP instead."""
        logger.warning("_fetch_hn_direct_api called but disabled; returning empty list")
        return []

    async def _fetch_brave_search_mcp(
        self,
        search_terms: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Perform web search using Brave Search MCP server.

        Args:
            search_terms: Search terms to query
            limit: Maximum number of results

        Returns:
            List of web search results

        """
        try:
            if not search_terms.strip():
                return []

            logger.info(f"Performing Brave Search via MCP for: {search_terms}")

            # Call Brave Search MCP directly
            if not self.mcp_manager:
                logger.warning("MCP manager not initialized")
                return []

            client = self.mcp_manager.get_client("brave_search")
            if not client:
                logger.warning("Brave Search MCP client not available")
                return []

            result = await client.call_tool(
                "brave_web_search",
                {
                    "query": search_terms,
                    "freshness": "pm",  # Past month for recent results
                    "count": BRAVE_WEB_SEARCH_LIMIT,
                },
            )

            # Check for MCP connection errors and handle gracefully
            if (
                isinstance(result, dict)
                and result.get("error") == "mcp_connection_failed"
            ):
                logger.warning(
                    "Brave Search MCP server unavailable, returning empty results",
                )
                return []

            if isinstance(result, dict) and "error" in result:
                logger.error(f"Brave Search MCP error: {result.get('error')}")
                return []

            # Parse the MCP response
            web_results = []
            if isinstance(result, dict) and "result" in result:
                brave_data = result["result"]
                # Check if brave_data has a "results" key
                if isinstance(brave_data, dict) and "results" in brave_data:
                    brave_results = brave_data["results"]
                else:
                    brave_results = brave_data if isinstance(brave_data, list) else []
            elif isinstance(result, list):
                brave_results = result
            else:
                logger.warning(
                    f"Unexpected Brave Search response format: {type(result)}",
                )
                return []
            
            # Ensure brave_results is a list before trying to iterate
            if not isinstance(brave_results, list):
                logger.warning(f"Brave results is not a list: {type(brave_results)}")
                return []
                
            for idx, item in enumerate(brave_results[:limit]):
                # Calculate relevance score using Brave Search result data
                score = self._calculate_brave_search_relevance(
                    item.get("title", ""),
                    item.get("url", ""),
                    item.get("description", ""),
                    search_terms,
                )

                web_result = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": "brave_search",
                    "score": score,
                    "timestamp": datetime.utcnow().isoformat(),  # Temporary, will be replaced by date extractor
                    "description": item.get(
                        "description",
                        f"Web search result for: {search_terms}",
                    ),
                    "tags": self._extract_tech_tags(item.get("title", "")),
                    "metadata": {
                        "search_terms": search_terms,
                        "rank": len(web_results) + 1,
                        "search_engine": "brave_search",
                        "language": item.get("language"),
                        "family_friendly": item.get("family_friendly"),
                    },
                }

                web_results.append(web_result)

            logger.info(f"Found {len(web_results)} Brave Search results")
            print(
                f"DEBUG: About to call filter_and_extract_dates with {len(web_results)} results",
            )

            # Apply clean date extraction and filtering (max 3 months old)
            try:
                logger.info(
                    f"Starting date extraction and filtering for {len(web_results)} results",
                )
                filtered_results = await filter_and_extract_dates(
                    web_results,
                    max_age_months=3,
                )
                logger.info(
                    f"After date filtering: {len(filtered_results)} recent results (within 3 months)",
                )
                print(
                    f"DEBUG: filter_and_extract_dates completed, got {len(filtered_results)} results",
                )
            except Exception as e:
                logger.error(f"Date filtering failed: {e}")
                print(f"DEBUG: Date filtering failed with error: {e}")
                # Fallback to original results if filtering fails
                filtered_results = web_results

            return filtered_results

        except Exception as e:
            logger.error(f"Brave Search MCP failed: {e}")
            return []

    # Old date extraction functions removed - now using clean DateExtractor utility

    def _calculate_brave_search_relevance(
        self,
        title: str,
        url: str,
        description: str,
        search_terms: str,
    ) -> int:
        """Calculate relevance score for Brave Search results.

        Args:
            title: Result title
            url: Result URL
            description: Result description
            search_terms: Search terms

        Returns:
            Relevance score (1-100)

        """
        if not title or not search_terms:
            return 30

        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        url_lower = url.lower() if url else ""
        terms = search_terms.lower().split()

        score = 15  # Base score

        # Quality indicators (higher score for authoritative sources)
        quality_domains = {
            "stackoverflow.com": 25,
            "github.com": 20,
            "medium.com": 15,
            "dev.to": 15,
            "geeksforgeeks.org": 15,
            "cppreference.com": 25,
            "mozilla.org": 20,
            "w3schools.com": 10,
            "wikipedia.org": 15,
            "hackernews.com": 20,
            "techcrunch.com": 15,
            "arstechnica.com": 20,
        }

        # Add quality bonus based on domain
        for domain, bonus in quality_domains.items():
            if domain in url_lower:
                score += bonus
                break

        # Term matching with different weights
        for term in terms:
            if len(term) > 2:
                # Title matches get highest score
                if term in title_lower:
                    if title_lower.count(term) > 1:
                        score += 30  # Multiple mentions in title
                    else:
                        score += 20  # Single mention in title

                # Description matches get medium score
                elif term in desc_lower:
                    score += 15

                # URL matches get medium score
                elif term in url_lower:
                    score += 12

                # Partial matches get lower score
                elif any(term in word for word in title_lower.split()):
                    score += 8

        # Bonus for exact phrase matches in title
        clean_terms = " ".join([t for t in terms if len(t) > 2])
        if clean_terms in title_lower:
            score += 25

        # Bonus for exact phrase matches in description
        if clean_terms in desc_lower:
            score += 15

        # Tech relevance bonus
        tech_keywords = [
            "api",
            "framework",
            "library",
            "python",
            "javascript",
            "react",
            "vue",
            "angular",
            "docker",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "ml",
            "ai",
            "database",
            "sql",
        ]
        for keyword in tech_keywords:
            if keyword in title_lower or keyword in desc_lower:
                score += 5
                break

        return min(100, max(1, score))

    def _combine_and_sort_trends(
        self,
        hn_results: list[dict[str, Any]],
        brave_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Combine and sort trends with HN first, then web results sorted by relevance and recency.

        Args:
            hn_results: Hacker News results
            brave_results: Web search results

        Returns:
            Combined and sorted list of trends

        """
        combined_trends = []

        # 1. Add HN results first (they're already sorted by HN score)
        if hn_results:
            # Sort HN results by score (highest first)
            hn_sorted = sorted(
                hn_results,
                key=lambda x: x.get("score", 0),
                reverse=True,
            )
            combined_trends.extend(hn_sorted)
            logger.info(f"Added {len(hn_sorted)} HN results first")

        # 2. Sort web search results by relevance score, then by recency
        if brave_results:
            # Sort by: 1) relevance score (desc), 2) timestamp (newest first)
            brave_sorted = sorted(
                brave_results,
                key=lambda x: (
                    x.get("score", 0),  # Primary: relevance score (higher = better)
                    x.get(
                        "timestamp",
                        "1970-01-01T00:00:00",
                    ),  # Secondary: timestamp (newer = better)
                ),
                reverse=True,
            )
            combined_trends.extend(brave_sorted)
            logger.info(
                f"Added {len(brave_sorted)} web search results sorted by relevance and recency",
            )

        logger.info(
            f"Combined total: {len(combined_trends)} trends (HN first, then web by relevance)",
        )
        return combined_trends
