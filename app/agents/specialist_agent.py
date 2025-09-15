"""Specialist Agent (Repo Intel) - Analyzes GitHub repositories and provides intelligence."""

from datetime import datetime
from typing import Any

from ..utils import get_logger
from .base_agent import BaseAgent

logger = get_logger(__name__)


class SpecialistAgent(BaseAgent):
    """Specialist Agent specializing in GitHub repository intelligence."""

    def __init__(self) -> None:
        """Initialize the Specialist Agent."""
        system_prompt = """
        You are the Repository Intelligence Agent, specializing in GitHub repository analysis and insights.
        
        Your responsibilities:
        1. Analyze GitHub repositories for metrics and activity
        2. Provide detailed repository intelligence reports
        3. Correlate repository data with technology trends
        4. Assess repository health and growth potential
        5. Identify related repositories and ecosystems
        6. Generate actionable insights for developers
        
        When analyzing repositories:
        - Focus on code quality indicators (stars, forks, activity)
        - Assess community engagement and maintenance
        - Identify technology stack and dependencies
        - Evaluate growth trends and momentum
        - Compare against similar repositories
        - Look for innovation and uniqueness factors
        
        Format your responses with:
        - Comprehensive repository profiles
        - Metric-based assessments
        - Technology ecosystem mapping
        - Growth and adoption insights
        - Competitive analysis
        - Risk and opportunity assessment
        """

        super().__init__("specialist_agent", system_prompt)

    async def process_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Process a repository intelligence request.

        Args:
            request_data: Request containing repository list and analysis preferences

        Returns:
            Repository intelligence analysis results

        """
        repositories = request_data.get("repositories", [])
        include_metrics = request_data.get("include_metrics", True)
        include_recent_activity = request_data.get("include_recent_activity", True)
        context = request_data.get("context", "")

        logger.info(
            "Processing repository intelligence request",
            repositories=repositories,
            include_metrics=include_metrics,
            include_recent_activity=include_recent_activity,
        )

        repo_data = []
        analysis_errors = []

        try:
            # Analyze each repository
            for repo_name in repositories[:10]:  # Limit to prevent rate limiting
                try:
                    repo_analysis = await self._analyze_repository(
                        repo_name,
                        include_metrics,
                        include_recent_activity,
                    )
                    if repo_analysis:
                        repo_data.append(repo_analysis)
                except Exception as e:
                    logger.error(f"Failed to analyze repository {repo_name}: {e}")
                    analysis_errors.append({"repository": repo_name, "error": str(e)})

            # Generate comprehensive analysis using AI
            if repo_data:
                analysis_prompt = f"""
                Analyze the following GitHub repositories with context: "{context}"
                
                Repository data: {repo_data}
                
                Provide a comprehensive analysis including:
                1. Repository health assessment
                2. Technology trends identification
                3. Community engagement evaluation
                4. Growth potential analysis
                5. Competitive landscape insights
                6. Recommendations for developers
                7. Risk factors and opportunities
                
                Focus on actionable insights and data-driven conclusions.
                """

                analysis_result = await self.agent.run(analysis_prompt)

                # Generate correlation analysis
                correlation_analysis = await self._generate_correlation_analysis(
                    repo_data,
                    context,
                )

                return {
                    "repositories": repo_data,
                    "total_repos": len(repo_data),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "insights": str(analysis_result),
                    "correlation_analysis": correlation_analysis,
                    "errors": analysis_errors,
                    "context": context,
                }
            return {
                "repositories": [],
                "total_repos": 0,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "insights": "No repositories could be analyzed successfully.",
                "errors": analysis_errors,
                "context": context,
            }

        except Exception as e:
            logger.error(f"Error processing repository intelligence request: {e}")
            return {
                "error": str(e),
                "repositories": repo_data,
                "total_repos": len(repo_data),
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "errors": analysis_errors,
                "context": context,
            }

    async def _analyze_repository(
        self,
        repo_name: str,
        include_metrics: bool = True,
        include_recent_activity: bool = True,
    ) -> dict[str, Any] | None:
        """Analyze a single GitHub repository.

        Args:
            repo_name: Repository name in owner/repo format
            include_metrics: Whether to include detailed metrics
            include_recent_activity: Whether to include recent activity data

        Returns:
            Repository analysis data or None if failed

        """
        try:
            # Parse owner and repo from name
            if "/" not in repo_name:
                logger.warning(f"Invalid repository name format: {repo_name}")
                return None

            owner, repo = repo_name.split("/", 1)

            # Get basic repository details
            basic_details_result = await self.agent.run(
                f"Get GitHub repository details using get_github_repo_details tool for owner: {owner} and repo: {repo}",
            )

            if (
                not basic_details_result
                or str(basic_details_result).strip() == ""
            ):
                logger.warning(f"No data returned for repository: {repo_name}")
                return None

            repo_data = str(basic_details_result)

            # Search for additional context if needed
            search_result = None
            if include_metrics:
                search_result = await self.agent.run(
                    f"Search GitHub repositories using search_github_repos tool with query: {repo_name}",
                )

            # Process and structure the data
            analysis = {
                "name": repo,
                "full_name": repo_name,
                "owner": owner,
                "description": repo_data.get("description", ""),
                "url": repo_data.get("html_url", f"https://github.com/{repo_name}"),
                "homepage": repo_data.get("homepage"),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "metrics": {
                    "stars": repo_data.get("stargazers_count", 0),
                    "forks": repo_data.get("forks_count", 0),
                    "watchers": repo_data.get("watchers_count", 0),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "size": repo_data.get("size", 0),
                    "default_branch": repo_data.get("default_branch", "main"),
                    "language": repo_data.get("language"),
                    "languages": {},  # Would need additional API call
                    "last_commit": repo_data.get("pushed_at"),
                    "commit_frequency": None,  # Would need additional analysis
                },
                "topics": repo_data.get("topics", []),
                "license": (
                    repo_data.get("license", {}).get("name")
                    if repo_data.get("license")
                    else None
                ),
                "is_fork": repo_data.get("fork", False),
                "archived": repo_data.get("archived", False),
                "metadata": {
                    "network_count": repo_data.get("network_count", 0),
                    "subscribers_count": repo_data.get("subscribers_count", 0),
                    "has_issues": repo_data.get("has_issues", True),
                    "has_projects": repo_data.get("has_projects", True),
                    "has_wiki": repo_data.get("has_wiki", True),
                    "visibility": repo_data.get("visibility", "public"),
                },
            }

            # Add search ranking if available
            if search_result and str(search_result).strip():
                search_data = str(search_result)
                if isinstance(search_data, dict) and "items" in search_data:
                    for i, item in enumerate(search_data["items"]):
                        if item.get("full_name") == repo_name:
                            analysis["metadata"]["search_rank"] = i + 1
                            break

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze repository {repo_name}: {e}")
            return None

    async def _generate_correlation_analysis(
        self,
        repo_data: list[dict[str, Any]],
        context: str,
    ) -> dict[str, Any]:
        """Generate correlation analysis between repositories and trends.

        Args:
            repo_data: List of repository analysis data
            context: Analysis context

        Returns:
            Correlation analysis results

        """
        try:
            if not repo_data:
                return {
                    "trending_technologies": [],
                    "related_repositories": [],
                    "correlation_score": 0.0,
                    "key_insights": ["No repositories to analyze"],
                    "growth_indicators": {},
                    "sentiment_analysis": "neutral",
                }

            # Extract technologies and metrics
            technologies = set()
            total_stars = 0
            total_forks = 0
            active_repos = 0

            for repo in repo_data:
                # Extract technologies from language and topics
                if repo.get("metrics", {}).get("language"):
                    technologies.add(repo["metrics"]["language"].lower())

                for topic in repo.get("topics", []):
                    technologies.add(topic.lower())

                # Aggregate metrics
                metrics = repo.get("metrics", {})
                total_stars += metrics.get("stars", 0)
                total_forks += metrics.get("forks", 0)

                # Check if repository is active (updated within reasonable time)
                if not repo.get("archived", False):
                    active_repos += 1

            avg_stars = total_stars / len(repo_data) if repo_data else 0
            avg_forks = total_forks / len(repo_data) if repo_data else 0
            activity_ratio = active_repos / len(repo_data) if repo_data else 0

            # Calculate correlation score based on various factors
            correlation_score = self._calculate_correlation_score(
                avg_stars,
                avg_forks,
                activity_ratio,
                len(technologies),
            )

            # Generate insights
            insights = []
            if avg_stars > 1000:
                insights.append("High community interest with significant star counts")
            if avg_forks > 100:
                insights.append("Strong development activity indicated by fork counts")
            if activity_ratio > 0.8:
                insights.append("Most repositories are actively maintained")
            if len(technologies) > 5:
                insights.append("Diverse technology ecosystem represented")

            return {
                "trending_technologies": list(technologies)[:10],  # Top 10
                "related_repositories": [repo["full_name"] for repo in repo_data],
                "correlation_score": correlation_score,
                "key_insights": insights,
                "growth_indicators": {
                    "average_stars": avg_stars,
                    "average_forks": avg_forks,
                    "activity_ratio": activity_ratio,
                    "technology_diversity": len(technologies),
                },
                "sentiment_analysis": self._assess_sentiment(avg_stars, activity_ratio),
            }

        except Exception as e:
            logger.error(f"Failed to generate correlation analysis: {e}")
            return {
                "trending_technologies": [],
                "related_repositories": [],
                "correlation_score": 0.0,
                "key_insights": [f"Analysis failed: {e!s}"],
                "growth_indicators": {},
                "sentiment_analysis": "unknown",
            }

    def _calculate_correlation_score(
        self,
        avg_stars: float,
        avg_forks: float,
        activity_ratio: float,
        tech_diversity: int,
    ) -> float:
        """Calculate correlation score based on repository metrics.

        Args:
            avg_stars: Average star count
            avg_forks: Average fork count
            activity_ratio: Ratio of active repositories
            tech_diversity: Number of different technologies

        Returns:
            Correlation score between 0.0 and 1.0

        """
        # Normalize individual scores
        star_score = min(avg_stars / 10000, 1.0)  # Normalize to 10k stars max
        fork_score = min(avg_forks / 1000, 1.0)  # Normalize to 1k forks max
        activity_score = activity_ratio  # Already 0-1
        diversity_score = min(tech_diversity / 20, 1.0)  # Normalize to 20 techs max

        # Weighted combination
        correlation_score = (
            star_score * 0.3
            + fork_score * 0.2
            + activity_score * 0.3
            + diversity_score * 0.2
        )

        return round(correlation_score, 3)

    def _assess_sentiment(self, avg_stars: float, activity_ratio: float) -> str:
        """Assess overall sentiment based on metrics.

        Args:
            avg_stars: Average star count
            activity_ratio: Ratio of active repositories

        Returns:
            Sentiment assessment

        """
        if avg_stars > 5000 and activity_ratio > 0.8:
            return "very_positive"
        if avg_stars > 1000 and activity_ratio > 0.6:
            return "positive"
        if avg_stars > 100 and activity_ratio > 0.4:
            return "neutral"
        if activity_ratio > 0.2:
            return "cautious"
        return "negative"

    async def handle_delegation_from_entry(
        self,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle delegation request from Entry Agent.

        Args:
            message: A2A message from Entry Agent

        Returns:
            Repository analysis response

        """
        payload = message.get("payload", {})
        repositories = payload.get("repositories", [])
        context = payload.get("context", "")

        logger.info(
            "Handling delegation from Entry Agent",
            repositories=repositories,
            context=context[:100] + "..." if len(context) > 100 else context,
        )

        # Process the repository analysis request
        request_data = {
            "repositories": repositories,
            "context": context,
            "include_metrics": True,
            "include_recent_activity": True,
        }

        result = await self.process_request(request_data)

        # Send response back to Entry Agent
        response_message = await self.send_message_to_agent(
            recipient="entry_agent",
            message_type="repo_analysis_response",
            payload=result,
        )

        return response_message.dict()
