"""Main FastAPI application for HN GitHub Agents."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .models import (
    AssistantRouteRequest,
    AssistantRouteResponse,
    CombinedAnalysisRequest,
    CombinedAnalysisResponse,
    ErrorResponse,
    GeneralChatRequest,
    GeneralChatResponse,
    HealthResponse,
    RepoIntelRequest,
    RepoIntelResponse,
    TechTrendsRequest,
    TechTrendsResponse,
)
from .services import AgentManager
from .services.history_service import HistoryService, build_default_history_service
from .services.memory_service import MemoryService, build_default_memory_service
from .utils import get_logger, settings, setup_logging

# Set up logging
setup_logging()
logger = get_logger(__name__)

# Global services
agent_manager: AgentManager = AgentManager()
history_service: HistoryService = build_default_history_service()
memory_service: MemoryService = build_default_memory_service()


# Old timestamp fixing function removed - now using clean DateExtractor utility


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting HN GitHub Agents application")
    try:
        await agent_manager.initialize()
        logger.info(
            f"The current configuration supports search for HN = {settings.hn_stories_limit} and web search = {settings.web_search_limit}",
        )
        logger.info("Application startup completed")
        # Mount A2A ASGI apps for each agent, if available
        try:
            if agent_manager.a2a_service and agent_manager.a2a_service.a2a_apps:
                for agent_name, a2a_app in agent_manager.a2a_service.a2a_apps.items():
                    mount_path = f"/a2a/{agent_name}"
                    app.mount(mount_path, a2a_app)
                logger.info("Mounted A2A ASGI apps for agents")
        except Exception as mount_err:
            logger.warning(f"Failed to mount A2A apps: {mount_err}")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down HN GitHub Agents application")
    try:
        await agent_manager.shutdown()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=settings.description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
# Configure CORS (restrict in production)
cors_origins = ["*"]
cors_allow_credentials = True
if settings.environment.lower() == "production":
    # In production, require explicit origins via ALLOWED_ORIGINS (comma-separated)
    if settings.allowed_origins:
        cors_origins = [
            o.strip() for o in settings.allowed_origins.split(",") if o.strip()
        ]
    else:
        cors_origins = []
    cors_allow_credentials = bool(settings.allow_credentials)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the UI (robust for local tests)
_candidate_static_dirs = [
    "/app/static",
    str(Path(__file__).resolve().parents[1] / "static"),
]
_static_dir = next((d for d in _candidate_static_dirs if os.path.isdir(d)), None)
if _static_dir:
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# A2A apps are mounted during lifespan after agent initialization


def get_agent_manager() -> AgentManager:
    """Dependency to get the agent manager instance."""
    if not agent_manager.initialized:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")
    return agent_manager


class A2ASendRequest(BaseModel):
    """A2A send message request model."""

    sender: str
    recipient: str
    message_type: str
    payload: dict[str, Any]
    correlation_id: str | None = None


@app.post("/a2a/send")
async def a2a_send(
    request: A2ASendRequest,
    manager: AgentManager = Depends(get_agent_manager),
):
    """Deliver an A2A message via HTTP to a recipient agent.
    Returns recipient handler output.
    """
    result = await manager.receive_a2a_message(
        recipient=request.recipient,
        message_type=request.message_type,
        payload=request.payload,
    )
    return {
        "status": "ok" if "error" not in result else "error",
        "result": result,
        "correlation_id": request.correlation_id,
    }


def get_history_service() -> HistoryService:
    """Dependency to get the history service instance."""
    return history_service


def get_memory_service() -> MemoryService:
    return memory_service


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Avoid leaking internal errors to clients in production
    message = (
        "An internal server error occurred"
        if settings.environment.lower() == "production"
        else str(exc)
    )
    error_response = ErrorResponse(
        error="internal_server_error",
        message=message,
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        status_code=500,
        content=error_response.dict(),
    )


@app.get("/")
async def root_json():
    """Root returns application JSON info (stable for tests)."""
    return {
        "name": settings.app_name,
        "description": settings.description,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs",
        "health_url": "/health",
        "ui_url": "/ui" if _static_dir else None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ui")
async def serve_ui():
    """Serve the main UI page if available."""
    if _static_dir:
        index_path = os.path.join(_static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="UI not available")


@app.get("/api", response_model=dict[str, Any])
async def root() -> dict[str, Any]:
    """Root API endpoint with application information."""
    return {
        "name": settings.app_name,
        "description": settings.description,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs",
        "health_url": "/health",
        "ui_url": "/",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(
    manager: AgentManager = Depends(get_agent_manager),
) -> HealthResponse:
    """Comprehensive health check endpoint."""
    try:
        health_data = await manager.health_check()

        # Determine overall status
        overall_status = "healthy"
        if not health_data.get("agent_manager", {}).get("initialized", False):
            overall_status = "degraded"

        # Check MCP servers
        mcp_servers = health_data.get("mcp_servers", {})
        if not all(mcp_servers.values()):
            overall_status = "degraded"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            mcp_servers=mcp_servers,
            agents_status={
                agent: data.get("status", "unknown")
                for agent, data in health_data.get("agents", {}).items()
            },
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/v1/trends", response_model=TechTrendsResponse)
async def analyze_tech_trends(
    request: TechTrendsRequest,
    background_tasks: BackgroundTasks,
    manager: AgentManager = Depends(get_agent_manager),
    history: HistoryService = Depends(get_history_service),
) -> TechTrendsResponse:
    """Analyze technology trends using Entry Agent."""
    logger.info(f"Tech trends analysis requested: {request.query}")

    try:
        # Convert request to dict for agent processing
        request_data = {
            "query": request.query,
            "limit": request.limit,
            "include_hn": request.include_hn,
            "include_brave": request.include_brave,
        }

        # Process request with Entry Agent
        result = await manager.process_tech_trends_request(request_data)

        # Log analysis completion in background
        background_tasks.add_task(
            log_analysis_completion,
            "tech_trends",
            request.query,
            len(result.get("trends", [])),
        )

        # Persist to history (best-effort; do not block response on errors)
        try:
            history.add_entry("trends", request.query, result)
        except Exception as _:
            pass

        # Convert result to response model
        return TechTrendsResponse(
            query=result["query"],
            trends=result.get("trends", []),
            total_items=result.get("total_items", 0),
            sources=result.get("sources", []),
            analysis_timestamp=datetime.fromisoformat(result["analysis_timestamp"]),
            summary=result.get("summary"),
        )

    except Exception as e:
        logger.error(f"Tech trends analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/repositories", response_model=RepoIntelResponse)
async def analyze_repositories(
    request: RepoIntelRequest,
    background_tasks: BackgroundTasks,
    manager: AgentManager = Depends(get_agent_manager),
) -> RepoIntelResponse:
    """Analyze GitHub repositories using Specialist Agent."""
    logger.info(f"Repository analysis requested: {request.repositories}")

    try:
        # Convert request to dict for agent processing
        request_data = {
            "repositories": request.repositories,
            "include_metrics": request.include_metrics,
            "include_recent_activity": request.include_recent_activity,
        }

        # Process request with Specialist Agent
        result = await manager.process_repo_intel_request(request_data)

        # Log analysis completion in background
        background_tasks.add_task(
            log_analysis_completion,
            "repository_intel",
            f"{len(request.repositories)} repositories",
            len(result.get("repositories", [])),
        )

        # Coerce repositories to full schema with sensible defaults for tests/mocks
        repos_in = result.get("repositories", [])
        coerced_repos = []
        now_dt = datetime.utcnow()
        for r in repos_in:
            full_name = r.get("full_name") or r.get("url", "").replace(
                "https://github.com/",
                "",
            )
            owner = r.get("owner") or (
                full_name.split("/")[0] if full_name and "/" in full_name else "unknown"
            )
            name = r.get("name") or (
                full_name.split("/")[-1] if full_name else "unknown"
            )
            url = r.get("url") or (
                f"https://github.com/{full_name}" if full_name else "https://github.com"
            )
            metrics = r.get("metrics", {})
            coerced_repos.append(
                {
                    "name": name,
                    "full_name": full_name or name,
                    "owner": owner,
                    "description": r.get("description", ""),
                    "url": url,
                    "homepage": r.get("homepage"),
                    "created_at": r.get("created_at", now_dt.isoformat()),
                    "updated_at": r.get("updated_at", now_dt.isoformat()),
                    "pushed_at": r.get("pushed_at"),
                    "metrics": {
                        "stars": metrics.get("stars", 0),
                        "forks": metrics.get("forks", 0),
                        "watchers": metrics.get("watchers", 0),
                        "open_issues": metrics.get("open_issues", 0),
                        "size": metrics.get("size", 0),
                        "default_branch": metrics.get("default_branch", "main"),
                        "language": metrics.get("language"),
                        "languages": metrics.get("languages", {}),
                        "last_commit": metrics.get(
                            "last_commit",
                            r.get("pushed_at", now_dt.isoformat()),
                        ),
                        "commit_frequency": metrics.get("commit_frequency"),
                    },
                    "topics": r.get("topics", []),
                    "license": r.get("license"),
                    "is_fork": r.get("is_fork", False),
                    "archived": r.get("archived", False),
                },
            )
        # Convert result to response model
        return RepoIntelResponse(
            repositories=coerced_repos,
            total_repos=result.get("total_repos", len(coerced_repos)),
            analysis_timestamp=datetime.fromisoformat(result["analysis_timestamp"]),
            insights=result.get("insights"),
        )

    except Exception as e:
        logger.error(f"Repository analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/combined-analysis", response_model=CombinedAnalysisResponse)
async def combined_analysis(
    request: CombinedAnalysisRequest,
    background_tasks: BackgroundTasks,
    manager: AgentManager = Depends(get_agent_manager),
) -> CombinedAnalysisResponse:
    """Perform combined tech trends and repository analysis using both agents."""
    logger.info(f"Combined analysis requested: {request.query}")

    try:
        # Convert request to dict for agent processing
        request_data = {
            "query": request.query,
            "auto_detect_repos": request.auto_detect_repos,
            "max_repos": request.max_repos,
            "trend_limit": request.trend_limit,
        }

        # Process request with both agents
        result = await manager.process_combined_analysis_request(request_data)

        # Log analysis completion in background
        background_tasks.add_task(
            log_analysis_completion,
            "combined_analysis",
            request.query,
            len(result.get("repositories", {}).get("repositories", [])),
        )

        # Convert result to response model
        trends_data = result["trends"]
        repos_data = result["repositories"]

        # Ensure correlation_analysis has required fields if missing in mocked data
        default_corr = {
            "trending_technologies": [],
            "related_repositories": [],
            "correlation_score": 0.0,
            "key_insights": [],
            "growth_indicators": {},
            "sentiment_analysis": "neutral",
        }
        return CombinedAnalysisResponse(
            query=result["query"],
            trends=TechTrendsResponse(
                query=trends_data["query"],
                trends=trends_data.get("trends", []),
                total_items=trends_data.get("total_items", 0),
                sources=trends_data.get("sources", []),
                analysis_timestamp=datetime.fromisoformat(
                    trends_data["analysis_timestamp"],
                ),
                summary=trends_data.get("summary"),
            ),
            repositories=RepoIntelResponse(
                repositories=repos_data.get("repositories", []),
                total_repos=repos_data.get("total_repos", 0),
                analysis_timestamp=datetime.fromisoformat(
                    repos_data["analysis_timestamp"],
                ),
                insights=repos_data.get("insights"),
            ),
            correlation_analysis=result.get("correlation_analysis") or default_corr,
            recommendations=result.get("recommendations", []),
            analysis_timestamp=datetime.fromisoformat(result["analysis_timestamp"]),
        )

    except Exception as e:
        logger.error(f"Combined analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents/status")
async def get_agents_status(
    manager: AgentManager = Depends(get_agent_manager),
) -> dict[str, Any]:
    """Get status of all agents."""
    try:
        health_data = await manager.health_check()
        return {
            "agents": health_data.get("agents", {}),
            "a2a_service": health_data.get("a2a_service", {}),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get agents status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/mcp/status")
async def get_mcp_status(
    manager: AgentManager = Depends(get_agent_manager),
) -> dict[str, Any]:
    """Get status of all MCP servers."""
    try:
        health_data = await manager.health_check()
        return {
            "mcp_servers": health_data.get("mcp_servers", {}),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get MCP status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/files")
async def list_available_files() -> dict[str, Any]:
    """List available files in the data directory for @ syntax."""
    import json
    from pathlib import Path

    if settings.environment.lower() == "production":
        # Do not expose filesystem listing in production
        return {
            "files": [],
            "source": "disabled",
            "timestamp": datetime.utcnow().isoformat(),
        }

    try:
        data_dir = Path("/app/data")
        files = []

        if data_dir.exists():
            # Recursively find all .json files in the data directory
            for json_file in data_dir.rglob("*.json"):
                try:
                    # Get relative path from data directory
                    relative_path = json_file.relative_to(data_dir)

                    # Try to read the file to get description
                    description = f"Data file: {json_file.name}"
                    try:
                        with open(json_file, encoding="utf-8") as f:
                            content = json.load(f)
                            # Try to extract description from common fields
                            if isinstance(content, dict):
                                if "Context" in content:
                                    description = content["Context"]
                                elif "description" in content:
                                    description = content["description"]
                                elif "metadata" in content and isinstance(
                                    content["metadata"],
                                    dict,
                                ):
                                    description = content["metadata"].get(
                                        "description",
                                        description,
                                    )
                                # Create description based on content
                                elif "sample_tech_trends" in content:
                                    description = (
                                        "Sample technology trends and popularity data"
                                    )
                                elif "mcp_servers" in content:
                                    description = (
                                        "MCP server configuration and tool definitions"
                                    )
                                elif any(
                                    key in content
                                    for key in ["repositories", "metrics", "github"]
                                ):
                                    description = (
                                        "GitHub repository metrics and analysis data"
                                    )
                                elif "Tools" in content:
                                    description = content.get(
                                        "Context",
                                        "AI tools and services data",
                                    )
                    except (json.JSONDecodeError, Exception):
                        # If we can't read the JSON, use a generic description
                        description = f"JSON data file: {json_file.name}"

                    files.append(
                        {
                            "name": json_file.name,
                            "path": str(relative_path),
                            "full_path": str(json_file),
                            "description": description,
                            "size": (
                                json_file.stat().st_size if json_file.exists() else 0
                            ),
                        },
                    )

                except Exception as file_error:
                    logger.warning(f"Error processing file {json_file}: {file_error}")
                    continue

        # Sort files by name for consistent ordering
        files.sort(key=lambda x: x["name"])

        logger.info(f"Found {len(files)} JSON files in data directory")

        return {
            "files": files,
            "source": "filesystem",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        # Return empty list instead of error to not break the UI
        return {
            "files": [],
            "source": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@app.post("/api/v1/chat", response_model=GeneralChatResponse)
async def general_chat(
    request: GeneralChatRequest,
    background_tasks: BackgroundTasks,
    manager: AgentManager = Depends(get_agent_manager),
    history: HistoryService = Depends(get_history_service),
) -> GeneralChatResponse:
    """Handle general AI chat for non-tech specific questions."""
    logger.info(f"General chat request: {request.message[:100]}...")

    try:
        # Process chat with Entry Agent (it has the dual capability)
        result = await manager.entry_agent.process_general_chat(request.message)

        # Log chat completion in background
        background_tasks.add_task(
            log_analysis_completion,
            "general_chat",
            request.message[:50],
            1,
        )

        # Persist to history
        try:
            history.add_entry("chat", request.message, result)
        except Exception:
            pass

        return GeneralChatResponse(
            response=result["response"],
            timestamp=datetime.fromisoformat(result["timestamp"]),
            message_type=result.get("message_type", "general"),
        )

    except Exception as e:
        logger.error(f"General chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/assistant", response_model=AssistantRouteResponse)
async def assistant_router(
    request: AssistantRouteRequest,
    manager: AgentManager = Depends(get_agent_manager),
    history: HistoryService = Depends(get_history_service),
):
    """Unified assistant endpoint that classifies and routes to trends or chat.

    - TECH → EntryAgent.process_request (trends)
    - GENERAL → EntryAgent.process_general_chat
    """
    try:
        routed = await manager.route_user_intent(
            request.input,
            limit=request.limit or 10,
            include_hn=request.include_hn,
            include_brave=request.include_brave,
        )
        # Save to history based on route
        try:
            history.add_entry(
                "chat" if routed["route"] == "chat" else "trends",
                request.input,
                routed.get("data", {}),
            )
        except Exception:
            pass
        return AssistantRouteResponse(
            route=routed["route"],
            data=routed["data"],
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Assistant routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/history")
async def get_history(
    history: HistoryService = Depends(get_history_service),
):
    """Return recent chat/trend entries for the sidebar."""
    items = [
        {
            "id": e.id,
            "type": e.type,
            "title": e.title,
            "input": e.input,
            "timestamp": datetime.fromisoformat(e.timestamp),
        }
        for e in history.get_recent()
    ]
    return {"items": items}


@app.get("/api/v1/history/{entry_id}")
async def get_history_entry(
    entry_id: str,
    history: HistoryService = Depends(get_history_service),
):
    entry = history.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    item = {
        "id": entry.id,
        "type": entry.type,
        "title": entry.title,
        "input": entry.input,
        "timestamp": datetime.fromisoformat(entry.timestamp),
    }
    return {"item": item, "data": entry.data}


async def log_analysis_completion(
    analysis_type: str,
    query: str,
    results_count: int,
) -> None:
    """Background task to log analysis completion."""
    logger.info(
        "Analysis completed",
        type=analysis_type,
        query=query[:100] + "..." if len(query) > 100 else query,
        results_count=results_count,
    )


if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
