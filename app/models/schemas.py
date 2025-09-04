"""Core data schemas for the application."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class TrendSource(str, Enum):
    """Enumeration of trend data sources."""

    HACKER_NEWS = "hacker_news"
    BRAVE_SEARCH = "brave_search"
    GITHUB = "github"


class TrendItem(BaseModel):
    """Individual trend item from various sources."""

    title: str = Field(description="Title of the trend item")
    url: HttpUrl | None = Field(description="URL to the trend item")
    source: TrendSource = Field(description="Source of the trend")
    score: int | None = Field(description="Score/ranking of the item")
    timestamp: datetime = Field(description="When the trend was captured")
    description: str | None = Field(description="Description or summary")
    tags: list[str] = Field(default_factory=list, description="Extracted tags/topics")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class HackerNewsStory(BaseModel):
    """Hacker News story data structure."""

    id: int = Field(description="Hacker News story ID")
    title: str = Field(description="Story title")
    url: HttpUrl | None = Field(description="Story URL")
    score: int = Field(description="Story score")
    by: str = Field(description="Author username")
    time: datetime = Field(description="Story timestamp")
    descendants: int | None = Field(description="Number of comments")
    text: str | None = Field(description="Story text content")
    type: str = Field(description="Story type (story, comment, etc.)")


class RepoMetrics(BaseModel):
    """GitHub repository metrics."""

    stars: int = Field(description="Number of stars")
    forks: int = Field(description="Number of forks")
    watchers: int = Field(description="Number of watchers")
    open_issues: int = Field(description="Number of open issues")
    size: int = Field(description="Repository size in KB")
    default_branch: str = Field(description="Default branch name")
    language: str | None = Field(description="Primary programming language")
    languages: dict[str, int] = Field(
        default_factory=dict,
        description="Languages breakdown",
    )
    last_commit: datetime | None = Field(description="Last commit timestamp")
    commit_frequency: float | None = Field(description="Average commits per week")


class GitHubRepository(BaseModel):
    """GitHub repository data structure."""

    name: str = Field(description="Repository name")
    full_name: str = Field(description="Full repository name (owner/repo)")
    owner: str = Field(description="Repository owner")
    description: str | None = Field(description="Repository description")
    url: HttpUrl = Field(description="Repository URL")
    homepage: HttpUrl | None = Field(description="Repository homepage")
    created_at: datetime = Field(description="Repository creation date")
    updated_at: datetime = Field(description="Last update timestamp")
    pushed_at: datetime | None = Field(description="Last push timestamp")
    metrics: RepoMetrics = Field(description="Repository metrics")
    topics: list[str] = Field(default_factory=list, description="Repository topics")
    license: str | None = Field(description="Repository license")
    is_fork: bool = Field(description="Whether the repository is a fork")
    archived: bool = Field(description="Whether the repository is archived")


class TrendAnalysis(BaseModel):
    """Analysis of trends and their correlation with repositories."""

    trending_technologies: list[str] = Field(
        description="Identified trending technologies",
    )
    related_repositories: list[str] = Field(
        description="Repositories related to trends",
    )
    correlation_score: float = Field(
        description="Correlation score between trends and repos",
        ge=0.0,
        le=1.0,
    )
    key_insights: list[str] = Field(description="Key insights from the analysis")
    growth_indicators: dict[str, float] = Field(
        description="Growth indicators for different technologies",
    )
    sentiment_analysis: str | None = Field(
        description="Overall sentiment about the trends",
    )


class AgentMessage(BaseModel):
    """Message structure for agent-to-agent communication."""

    sender_agent: str = Field(description="Name of the sending agent")
    recipient_agent: str = Field(description="Name of the recipient agent")
    message_type: str = Field(description="Type of message")
    payload: dict[str, Any] = Field(description="Message payload")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp",
    )
    correlation_id: str | None = Field(
        description="Correlation ID for request tracking",
    )


class MCPToolResult(BaseModel):
    """Result from an MCP tool execution."""

    tool_name: str = Field(description="Name of the MCP tool")
    success: bool = Field(description="Whether the tool execution was successful")
    result: dict[str, Any] | None = Field(description="Tool execution result")
    error: str | None = Field(description="Error message if execution failed")
    execution_time: float = Field(description="Tool execution time in seconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Execution timestamp",
    )
