"""Configuration settings for the application."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # MCP Server URLs
    brave_search_mcp_url: str = Field(
        default="http://localhost:3001",
        env="BRAVE_SEARCH_MCP_URL",
    )
    github_mcp_url: str = Field(default="http://localhost:3002", env="GITHUB_MCP_URL")
    hacker_news_mcp_url: str = Field(
        default="http://localhost:3003",
        env="HACKER_NEWS_MCP_URL",
    )
    filesystem_mcp_url: str = Field(
        default="http://localhost:3004",
        env="FILESYSTEM_MCP_URL",
    )

    # GitHub Configuration
    github_token: str | None = Field(default=None, env="GITHUB_TOKEN")

    # Application Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    allowed_origins: str | None = Field(default=None, env="ALLOWED_ORIGINS")
    allow_credentials: bool = Field(default=False, env="ALLOW_CREDENTIALS")

    # Hacker News Configuration
    hn_stories_limit: int = Field(default=50, env="HN_STORIES_LIMIT")

    # Web Search Configuration
    web_search_limit: int = Field(default=20, env="WEB_SEARCH_LIMIT")

    # Brave MCP optional settings (ignore if not provided)
    brave_api_key: str | None = Field(default=None, env="BRAVE_API_KEY")
    brave_web_search_limit: int | None = Field(
        default=None,
        env="BRAVE_WEB_SEARCH_LIMIT",
    )
    brave_image_search_limit: int | None = Field(
        default=None,
        env="BRAVE_IMAGE_SEARCH_LIMIT",
    )
    brave_news_search_limit: int | None = Field(
        default=None,
        env="BRAVE_NEWS_SEARCH_LIMIT",
    )
    brave_video_search_limit: int | None = Field(
        default=None,
        env="BRAVE_VIDEO_SEARCH_LIMIT",
    )
    brave_summarizer_limit: int | None = Field(
        default=None,
        env="BRAVE_SUMMARIZER_LIMIT",
    )

    # FastAPI Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")

    # A2A Configuration
    a2a_server_host: str = Field(default="localhost", env="A2A_SERVER_HOST")
    a2a_server_port: int = Field(default=8001, env="A2A_SERVER_PORT")

    # Application Metadata
    app_name: str = "HN GitHub Agents"
    app_version: str = "0.1.0"
    description: str = "PyCon Demo: FastAPI + Pydantic-AI + MCP Servers"

    # Rate Limiting
    hacker_news_rate_limit: int = Field(
        default=30,
        description="HN API calls per minute",
    )
    github_rate_limit: int = Field(default=60, description="GitHub API calls per hour")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
