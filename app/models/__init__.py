"""Data models for the HN GitHub Agents application."""

from .requests import (
    AssistantRouteRequest,
    CombinedAnalysisRequest,
    GeneralChatRequest,
    RepoIntelRequest,
    TechTrendsRequest,
)
from .responses import (
    AssistantRouteResponse,
    CombinedAnalysisResponse,
    ErrorResponse,
    GeneralChatResponse,
    HealthResponse,
    HistoryEntryResponse,
    HistoryItem,
    HistoryListResponse,
    RepoIntelResponse,
    TechTrendsResponse,
)
from .schemas import (
    GitHubRepository,
    HackerNewsStory,
    RepoMetrics,
    TrendAnalysis,
    TrendItem,
)

__all__ = [
    "AssistantRouteRequest",
    "AssistantRouteResponse",
    "CombinedAnalysisRequest",
    "CombinedAnalysisResponse",
    "ErrorResponse",
    "GeneralChatRequest",
    "GeneralChatResponse",
    "GitHubRepository",
    "HackerNewsStory",
    "HealthResponse",
    "HistoryEntryResponse",
    "HistoryItem",
    "HistoryListResponse",
    "RepoIntelRequest",
    "RepoIntelResponse",
    "RepoMetrics",
    "TechTrendsRequest",
    "TechTrendsResponse",
    "TrendAnalysis",
    "TrendItem",
]
