"""Response models for API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .schemas import GitHubRepository, TrendAnalysis, TrendItem


class TechTrendsResponse(BaseModel):
    """Response model for tech trends analysis."""

    query: str = Field(description="Original query")
    trends: list[TrendItem] = Field(description="List of trend items")
    total_items: int = Field(description="Total number of trend items found")
    sources: list[str] = Field(description="Data sources used")
    analysis_timestamp: datetime = Field(description="When the analysis was performed")
    summary: str | None = Field(description="AI-generated summary of trends")


class RepoIntelResponse(BaseModel):
    """Response model for repository intelligence analysis."""

    repositories: list[GitHubRepository] = Field(description="Repository data")
    total_repos: int = Field(description="Total number of repositories analyzed")
    analysis_timestamp: datetime = Field(description="When the analysis was performed")
    insights: str | None = Field(
        description="AI-generated insights about repositories",
    )


class CombinedAnalysisResponse(BaseModel):
    """Response model for combined analysis."""

    query: str = Field(description="Original query")
    trends: TechTrendsResponse = Field(description="Tech trends analysis")
    repositories: RepoIntelResponse = Field(description="Repository intelligence")
    correlation_analysis: TrendAnalysis = Field(
        description="Correlation between trends and repos",
    )
    recommendations: list[str] = Field(description="AI-generated recommendations")
    analysis_timestamp: datetime = Field(description="When the analysis was performed")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(description="Service status")
    timestamp: datetime = Field(description="Health check timestamp")
    version: str = Field(description="Application version")
    mcp_servers: dict[str, bool] = Field(description="MCP server availability")
    agents_status: dict[str, str] = Field(description="Agent status information")


class ErrorResponse(BaseModel):
    """Response model for error cases."""

    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: dict[str, Any] | None = Field(description="Additional error details")
    timestamp: datetime = Field(description="Error timestamp")


class GeneralChatResponse(BaseModel):
    """Response model for general AI chat."""

    response: str = Field(description="AI assistant's response to the user's message")
    timestamp: datetime = Field(description="When the response was generated")
    message_type: str = Field(
        default="general",
        description="Type of message - 'general' for non-tech queries",
    )


class AssistantRouteResponse(BaseModel):
    """Unified assistant response that includes routing decision."""

    route: str = Field(description="Which route was taken: 'trends' or 'chat'")
    data: dict[str, Any] = Field(description="Response payload from the selected route")
    timestamp: datetime = Field(description="When the response was generated")


class HistoryItem(BaseModel):
    """Sidebar-friendly history item."""

    id: str = Field(description="Unique ID of the history entry")
    type: str = Field(description="'trends' or 'chat'")
    title: str = Field(description="Short title for UI display")
    input: str = Field(description="Original user input")
    timestamp: datetime = Field(description="When the entry was created")


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]


class HistoryEntryResponse(BaseModel):
    item: HistoryItem
    data: dict[str, Any]
