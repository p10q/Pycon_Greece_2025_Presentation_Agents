### Building Production‑Ready AI Agents with FastAPI, Pydantic‑AI & MCP

Timebox: 15–20 minutes. Goal: Show how this repo wires Pydantic‑AI agents, MCP tools, A2A messaging, and a simple UI, with concrete file pointers and runnable calls.

---

## 0) Setup (30–60s)
- **Run locally**:
  - `uvicorn app.main:app --reload` (or use `docker-start.sh` if you prefer containers)
- **Open UI**: `http://localhost:8000/ui`
- **Docs**: `http://localhost:8000/docs`

If MCP servers aren’t running, the app gracefully degrades; endpoints still respond. Optional: start bundled MCPs via `docker-compose up -d`.

## 1) FastAPI entrypoint and lifecycle (2 min)
- File: `app/main.py`
  - Show `lifespan()` where `AgentManager.initialize()` runs, and A2A ASGI apps mount at `/a2a/{agent}`.
  - Highlight CORS + static mounting for the UI.

Code anchors to display briefly:
```python
180:201:app/main.py
@app.get("/ui")
async def serve_ui():
    if _static_dir:
        index_path = os.path.join(_static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="UI not available")
```

```python
51:69:app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await agent_manager.initialize()
    if agent_manager.a2a_service and agent_manager.a2a_service.a2a_apps:
        for agent_name, a2a_app in agent_manager.a2a_service.a2a_apps.items():
            app.mount(f"/a2a/{agent_name}", a2a_app)
```

---

## 2) Pydantic‑AI agents (4 min)
- Base wiring: `app/agents/base_agent.py`
  - `Agent(model=OpenAIModel("gpt-4o"), system_prompt=...)`
  - Tools registered via `@self.agent.tool` mapping to MCP calls: `search_brave`, `get_hacker_news_stories`, `search_github_repos`, `get_github_repo_details`, `read_file`.

Code anchors:
```python
39:47:app/agents/base_agent.py
self.agent = Agent(
    model=OpenAIModel("gpt-4o"),
    system_prompt=self.system_prompt,
)
self._register_tools()
```

```python
51:76:app/agents/base_agent.py
@self.agent.tool
async def search_brave(ctx: RunContext[Any], query: str, freshness: str = "pm"):
    client = self.mcp_manager.get_client("brave_search")
    result = await client.call_tool("brave_web_search", {"query": query, "freshness": freshness, "count": BRAVE_WEB_SEARCH_LIMIT})
    return result
```

- Entry Agent: `app/agents/entry_agent.py`
  - Dual‑mode classifier TECH vs GENERAL, tech trends flow using MCP (Brave + HN), repo detection, optional A2A delegation.

```python
66:89:app/agents/entry_agent.py
async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    query = request_data.get("query", "")
    include_hn = request_data.get("include_hn", True)
    include_brave = request_data.get("include_brave", True)
    limit = request_data.get("limit", 10)
    query = await self._process_file_references(query)
```

- Specialist Agent: `app/agents/specialist_agent.py`
  - Uses Pydantic‑AI tools to enrich repo intel and returns structured results.

---

## 3) MCP integration (3 min)
- Client manager: `app/utils/mcp_client.py`
  - `MCPClientManager.__aenter__()` instantiates clients for `brave_search`, `hacker_news`, `github`, `filesystem` using env settings.
  - `MCPClient.call_tool()` abstracts POST to `/tools/{name}`.

Code anchors:
```python
139:160:app/utils/mcp_client.py
class MCPClientManager:
    async def __aenter__(self) -> "MCPClientManager":
        client_configs = {
            "brave_search": settings.brave_search_mcp_url,
            "github": settings.github_mcp_url,
            "hacker_news": settings.hacker_news_mcp_url,
            "filesystem": settings.filesystem_mcp_url,
        }
        for name, url in client_configs.items():
            if url and url.strip():
                self.clients[name] = MCPClient(url, name)
        for client in self.clients.values():
            await client.__aenter__()
        return self
```

```python
84:101:app/utils/mcp_client.py
response = await self.client.post(
    f"{self.server_url}/tools/{tool_name}",
    json=payload,
)
response.raise_for_status()
return response.json()
```

Talking point: graceful degradation — if MCP is down, tools return `{error: "mcp_connection_failed"}` and the app continues.

---

## 4) Agent‑to‑Agent (A2A) messaging (3 min)
- Manager: `app/services/agent_manager.py`
  - Initializes agents + `A2AService`, registers each agent’s `.to_a2a()`.
  - Routes assistant requests and demonstrates A2A handoff from `GeneralAgent` to `EntryAgent`.

```python
133:171:app/services/agent_manager.py
async def route_user_intent(...):
    general_result = await self.general_agent.process_request({...})
    if general_result.get("handoff"):
        await self.a2a_service.send_message(
            sender="general_agent",
            recipient="entry_agent",
            message_type="tech_trends_request",
            payload=payload,
        )
        data = await self.entry_agent.process_request(trends_request)
        return {"route": "trends", "data": data}
    return {"route": "chat", "data": general_result}
```

- Service: `app/services/a2a_service.py`
  - Keeps registry, exposes `agent.to_a2a()` ASGI apps, provides HTTP fallback via `/a2a/send`.

```python
45:63:app/services/a2a_service.py
async def register_agent(self, agent_name: str, agent: Any) -> None:
    self.agents[agent_name] = agent
    self.a2a_apps[agent_name] = agent.to_a2a()
```

```python
124:136:app/services/a2a_service.py
logger.info(
    "A2A message sent",
    sender=sender,
    recipient=recipient,
    message_type=message_type,
    correlation_id=message.correlation_id,
)
```

Live call (optional):
```bash
curl -s http://localhost:8000/a2a/send \
  -H 'Content-Type: application/json' \
  -d '{
    "sender": "general_agent",
    "recipient": "entry_agent",
    "message_type": "tech_trends_request",
    "payload": {"query": "python agents", "limit": 5}
  }'
```

---

## 5) API and UI demo (3–5 min)
- Endpoints: `app/main.py`
  - `/api/v1/trends` → Entry Agent via `AgentManager.process_tech_trends_request`
  - `/api/v1/assistant` → intent routing + A2A handoff
  - `/api/v1/mcp/status`, `/api/v1/agents/status` for health visibility

Commands:
```bash
# Health
curl -s http://localhost:8000/health | jq .

# Trends
curl -s -X POST http://localhost:8000/api/v1/trends \
  -H 'Content-Type: application/json' \
  -d '{"query":"Python AI frameworks 2025","limit":8,"include_hn":true,"include_brave":true}' | jq .summary

# Unified assistant (routes to chat or trends)
curl -s -X POST http://localhost:8000/api/v1/assistant \
  -H 'Content-Type: application/json' \
  -d '{"input":"What are the current JS framework trends?","limit":6}' | jq .route
```

- UI: `static/index.html`, `static/app.js`
  - Shows toggles HN/Web, renders trends grid, AI summary, and repo detection. Point out the `@filename.json` inline‑data feature handled by `EntryAgent._process_file_references()`.

---

## 6) Attendee takeaways (30s)
- **Pydantic‑AI**: ergonomic agent and tool registration; model‑agnostic with clean prompts.
- **MCP**: clean boundary for external capabilities; resilient when remote tools fail.
- **A2A**: simple multi‑agent orchestration; HTTP fallback and ASGI exposure.
- **FastAPI + UI**: production‑friendly serving with health checks, docs, and a minimal frontend.

---

## Optional troubleshooting notes
- If MCP URLs aren’t configured, endpoints still respond; results may be empty or mocked. Check env vars in `env.example` and `app/utils/config.py`.
- On connection issues, see logs; many tool calls return `{error: "mcp_connection_failed"}` without crashing flows.

---

## Stretch (only if time remains)
- Show `Combined Analysis` flow: POST `/api/v1/combined-analysis` and how repos auto‑detected by Entry Agent feed the Specialist Agent.


---

## Full session timing plan (20–25 min + 10 min wrap‑up)
- Main live demo (FastAPI + Pydantic‑AI quick warm‑up + multi‑agent app): 20–25 minutes total
  - 0.5) FastAPI + Pydantic‑AI quick warm‑up: 90–180 seconds
  - 1) FastAPI entrypoint and lifecycle: ~2 minutes
  - 2) Pydantic‑AI agents: ~4 minutes
  - 3) MCP integration: ~3 minutes
  - 4) A2A messaging: ~3 minutes
  - 5) API and UI demo: ~3–5 minutes
- Audience survey: ~5 minutes
- Q&A: ~5 minutes

