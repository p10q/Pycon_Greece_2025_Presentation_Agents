"""Request models for API endpoints."""


from pydantic import BaseModel, Field


class TechTrendsRequest(BaseModel):
    """Request model for tech trends analysis."""

    query: str = Field(
        ...,
        description="Query for tech trends analysis",
        min_length=1,
        max_length=500,
        examples=["latest AI frameworks", "Python web development trends"],
    )
    limit: int | None = Field(
        default=10,
        description="Number of trend items to return",
        ge=1,
        le=50,
    )
    include_hn: bool = Field(
        default=True,
        description="Whether to include Hacker News stories",
    )
    include_brave: bool = Field(
        default=True,
        description="Whether to include Brave Search results",
    )


class RepoIntelRequest(BaseModel):
    """Request model for repository intelligence analysis."""

    repositories: list[str] = Field(
        ...,
        description="List of repository names (owner/repo format)",
        min_items=1,
        max_items=20,
        examples=[["microsoft/vscode", "facebook/react"]],
    )
    include_metrics: bool = Field(
        default=True,
        description="Whether to include detailed repository metrics",
    )
    include_recent_activity: bool = Field(
        default=True,
        description="Whether to include recent activity data",
    )


class CombinedAnalysisRequest(BaseModel):
    """Request model for combined tech trends and repository analysis."""

    query: str = Field(
        ...,
        description="Query for tech trends analysis",
        min_length=1,
        max_length=500,
    )
    auto_detect_repos: bool = Field(
        default=True,
        description="Whether to automatically detect repositories from trends",
    )
    max_repos: int | None = Field(
        default=5,
        description="Maximum number of repositories to analyze",
        ge=1,
        le=10,
    )
    trend_limit: int | None = Field(
        default=10,
        description="Number of trend items to analyze",
        ge=1,
        le=30,
    )


class GeneralChatRequest(BaseModel):
    """Request model for general AI chat (non-tech specific queries)."""

    message: str = Field(
        ...,
        description="General question or message for the AI assistant",
        min_length=1,
        max_length=1000,
        examples=[
            "Where is Athens?",
            "How does photosynthesis work?",
            "What is the capital of France?",
        ],
    )


class AssistantRouteRequest(BaseModel):
    """Unified assistant request model for intent-based routing."""

    input: str = Field(
        ...,
        description="User input that will be classified and routed to the correct pipeline",
        min_length=1,
        max_length=1000,
        examples=[
            "Where is Athens?",
            "Python web frameworks trends",
            "@tech_trends_sample.json What is hot right now?",
        ],
    )
    # Optional overrides for trends path
    limit: int | None = Field(default=10, ge=1, le=50)
    include_hn: bool = Field(default=True)
    include_brave: bool = Field(default=True)
