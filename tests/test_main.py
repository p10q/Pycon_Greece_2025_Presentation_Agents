"""Tests for the main FastAPI application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_agent_manager():
    """Create a mock agent manager."""
    manager = MagicMock()
    manager.initialized = True
    manager.health_check = AsyncMock(
        return_value={
            "agent_manager": {"status": "healthy", "initialized": True},
            "agents": {
                "entry_agent": {"status": "healthy"},
                "specialist_agent": {"status": "healthy"},
            },
            "mcp_servers": {
                "brave_search": True,
                "github": True,
                "hacker_news": True,
                "filesystem": True,
            },
            "a2a_service": {"server_running": True},
        },
    )
    return manager


class TestMainEndpoints:
    """Test cases for main application endpoints."""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns application info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "description" in data
        assert "version" in data
        assert data["name"] == "HN GitHub Agents"

    @patch("app.main.agent_manager")
    def test_health_check_healthy(self, mock_manager, client):
        """Test health check when all services are healthy."""
        mock_manager.initialized = True
        mock_manager.health_check = AsyncMock(
            return_value={
                "agent_manager": {"status": "healthy", "initialized": True},
                "agents": {
                    "entry_agent": {"status": "healthy"},
                    "specialist_agent": {"status": "healthy"},
                },
                "mcp_servers": {
                    "brave_search": True,
                    "github": True,
                    "hacker_news": True,
                    "filesystem": True,
                },
            },
        )

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "mcp_servers" in data
        assert "agents_status" in data

    @patch("app.main.agent_manager")
    def test_health_check_degraded(self, mock_manager, client):
        """Test health check when some services are down."""
        mock_manager.initialized = True
        mock_manager.health_check = AsyncMock(
            return_value={
                "agent_manager": {"status": "healthy", "initialized": True},
                "agents": {
                    "entry_agent": {"status": "healthy"},
                    "specialist_agent": {"status": "healthy"},
                },
                "mcp_servers": {
                    "brave_search": False,  # This service is down
                    "github": True,
                    "hacker_news": True,
                    "filesystem": True,
                },
            },
        )

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["mcp_servers"]["brave_search"] == False

    def test_health_check_not_initialized(self, client):
        """Test health check when agent manager is not initialized."""
        with patch("app.main.agent_manager") as mock_manager:
            mock_manager.initialized = False

            response = client.get("/health")
            assert response.status_code == 503


class TestTechTrendsEndpoint:
    """Test cases for tech trends analysis endpoint."""

    @patch("app.main.agent_manager")
    def test_analyze_tech_trends_success(self, mock_manager, client):
        """Test successful tech trends analysis."""
        mock_manager.initialized = True
        mock_manager.process_tech_trends_request = AsyncMock(
            return_value={
                "query": "FastAPI trends",
                "trends": [
                    {
                        "title": "FastAPI is trending",
                        "url": "https://example.com",
                        "source": "hacker_news",
                        "score": 100,
                        "timestamp": "2024-01-15T10:00:00",
                        "description": "FastAPI framework gaining popularity",
                        "tags": ["fastapi", "python"],
                        "metadata": {},
                    },
                ],
                "total_items": 1,
                "sources": ["hacker_news"],
                "analysis_timestamp": "2024-01-15T10:00:00",
                "summary": "FastAPI is trending upward",
            },
        )

        request_data = {
            "query": "FastAPI trends",
            "limit": 10,
            "include_hn": True,
            "include_brave": True,
        }

        response = client.post("/api/v1/trends", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "FastAPI trends"
        assert len(data["trends"]) == 1
        assert data["total_items"] == 1

    @patch("app.main.agent_manager")
    def test_analyze_tech_trends_validation_error(self, mock_manager, client):
        """Test tech trends analysis with validation error."""
        mock_manager.initialized = True

        # Missing required query field
        request_data = {"limit": 10}

        response = client.post("/api/v1/trends", json=request_data)
        assert response.status_code == 422  # Validation error


class TestRepositoryEndpoint:
    """Test cases for repository analysis endpoint."""

    @patch("app.main.agent_manager")
    def test_analyze_repositories_success(self, mock_manager, client):
        """Test successful repository analysis."""
        mock_manager.initialized = True
        mock_manager.process_repo_intel_request = AsyncMock(
            return_value={
                "repositories": [
                    {
                        "name": "fastapi",
                        "full_name": "tiangolo/fastapi",
                        "owner": "tiangolo",
                        "description": "FastAPI framework",
                        "url": "https://github.com/tiangolo/fastapi",
                        "metrics": {"stars": 75000, "forks": 6200},
                    },
                ],
                "total_repos": 1,
                "analysis_timestamp": "2024-01-15T10:00:00",
                "insights": "FastAPI is a popular framework",
            },
        )

        request_data = {
            "repositories": ["tiangolo/fastapi"],
            "include_metrics": True,
            "include_recent_activity": True,
        }

        response = client.post("/api/v1/repositories", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert len(data["repositories"]) == 1
        assert data["total_repos"] == 1
        assert data["repositories"][0]["full_name"] == "tiangolo/fastapi"


class TestAssistantEndpoint:
    """Tests for unified assistant endpoint."""

    @patch("app.main.agent_manager")
    def test_assistant_routes_to_chat(self, mock_manager, client):
        mock_manager.initialized = True

        # Simulate manager.route_user_intent returning chat
        async def route_user_intent(input_text: str, **kwargs):
            return {
                "route": "chat",
                "data": {
                    "response": "Athens is the capital of Greece.",
                    "timestamp": "2024-01-15T10:00:00",
                    "message_type": "general",
                },
            }

        mock_manager.route_user_intent = AsyncMock(side_effect=route_user_intent)

        response = client.post(
            "/api/v1/assistant",
            json={
                "input": "What is the weather in Athens?",
                "limit": 10,
                "include_hn": True,
                "include_brave": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["route"] == "chat"
        assert "data" in data and "response" in data["data"]

    @patch("app.main.agent_manager")
    def test_assistant_routes_to_trends(self, mock_manager, client):
        mock_manager.initialized = True

        # Simulate manager.route_user_intent returning trends
        async def route_user_intent(input_text: str, **kwargs):
            return {
                "route": "trends",
                "data": {
                    "query": input_text,
                    "trends": [],
                    "total_items": 0,
                    "sources": ["hacker_news"],
                    "analysis_timestamp": "2024-01-15T10:00:00",
                    "summary": "",
                },
            }

        mock_manager.route_user_intent = AsyncMock(side_effect=route_user_intent)

        response = client.post(
            "/api/v1/assistant",
            json={
                "input": "Python web frameworks 2024",
                "limit": 10,
                "include_hn": True,
                "include_brave": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["route"] == "trends"
        assert "data" in data and "trends" in data["data"]


class TestCombinedAnalysisEndpoint:
    """Test cases for combined analysis endpoint."""

    @patch("app.main.agent_manager")
    def test_combined_analysis_success(self, mock_manager, client):
        """Test successful combined analysis."""
        mock_manager.initialized = True
        mock_manager.process_combined_analysis_request = AsyncMock(
            return_value={
                "query": "AI frameworks",
                "trends": {
                    "query": "AI frameworks",
                    "trends": [],
                    "total_items": 0,
                    "sources": ["hacker_news"],
                    "analysis_timestamp": "2024-01-15T10:00:00",
                    "summary": "AI frameworks trending",
                },
                "repositories": {
                    "repositories": [],
                    "total_repos": 0,
                    "analysis_timestamp": "2024-01-15T10:00:00",
                    "insights": "No repositories analyzed",
                },
                "correlation_analysis": {},
                "recommendations": ["Explore AI frameworks"],
                "analysis_timestamp": "2024-01-15T10:00:00",
            },
        )

        request_data = {
            "query": "AI frameworks",
            "auto_detect_repos": True,
            "max_repos": 5,
            "trend_limit": 10,
        }

        response = client.post("/api/v1/combined-analysis", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "AI frameworks"
        assert "trends" in data
        assert "repositories" in data
        assert "recommendations" in data


class TestStatusEndpoints:
    """Test cases for status endpoints."""

    @patch("app.main.agent_manager")
    def test_agents_status(self, mock_manager, client):
        """Test agents status endpoint."""
        mock_manager.initialized = True
        mock_manager.health_check = AsyncMock(
            return_value={
                "agents": {
                    "entry_agent": {"status": "healthy"},
                    "specialist_agent": {"status": "healthy"},
                },
                "a2a_service": {"server_running": True},
            },
        )

        response = client.get("/api/v1/agents/status")
        assert response.status_code == 200

        data = response.json()
        assert "agents" in data
        assert "a2a_service" in data

    @patch("app.main.agent_manager")
    def test_mcp_status(self, mock_manager, client):
        """Test MCP servers status endpoint."""
        mock_manager.initialized = True
        mock_manager.health_check = AsyncMock(
            return_value={
                "mcp_servers": {
                    "brave_search": True,
                    "github": True,
                    "hacker_news": False,
                    "filesystem": True,
                },
            },
        )

        response = client.get("/api/v1/mcp/status")
        assert response.status_code == 200

        data = response.json()
        assert "mcp_servers" in data
        assert data["mcp_servers"]["brave_search"] == True
        assert data["mcp_servers"]["hacker_news"] == False
