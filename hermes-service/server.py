"""
Hermes Service — HTTP wrapper for Hermes AIAgent
-------------------------------------------------
Lightweight FastAPI server that exposes Hermes AIAgent via:
  POST /query    — run a query with SSE streaming
  GET  /health   — health check

The bridge talks to this service over HTTP instead of importing AIAgent directly.
This allows Hermes to run in its own container with isolated dependencies.

SSE event types sent to the client:
  event: delta      data: {"delta": "text chunk"}
  event: tool       data: {"tool": "tool_name", "status": "running", "preview": "..."}
  event: status     data: {"message": "Thinking..."}
  event: done       data: {"response": "full text", "messages": [...], "dashboard": {...}}
  event: error      data: {"error": "message"}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

# ---------------------------------------------------------------------------
# Hermes AIAgent import
# ---------------------------------------------------------------------------

HERMES_AGENT_DIR = os.getenv(
    "HERMES_AGENT_DIR",
    os.path.join(os.path.dirname(__file__), "..", "hermes-agent"),
)
if os.path.isdir(HERMES_AGENT_DIR) and HERMES_AGENT_DIR not in sys.path:
    sys.path.insert(0, HERMES_AGENT_DIR)

from run_agent import AIAgent  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HERMES_PORT = int(os.getenv("HERMES_PORT", "8002"))
HERMES_MODEL = os.getenv("HERMES_MODEL", "qwen/qwen3-235b-a22b")
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "https://openrouter.ai/api/v1")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
HERMES_MAX_ITERATIONS = int(os.getenv("HERMES_MAX_ITERATIONS", "20"))
MCP_URL = os.getenv("MCP_URL", "http://mcp-wrapper:8000/mcp/")

SYSTEM_PROMPT = """You are DocuMentor, an intelligent document analysis assistant for universities.
You help users understand, query, and extract insights from their uploaded documents.

You have access to SurfSense tools for document management and querying.
When answering questions:
1. Use the available search/query tools to find relevant information in the knowledge base.
2. Always cite which documents your information comes from.
3. If you can extract structured data (tables, metrics, KPIs), format it as JSON for dashboard rendering.
4. Be concise but thorough. Answer in the same language the user writes in.
5. If no relevant documents are found, say so honestly.

You are running inside DocuMentor, a self-hosted document intelligence platform.
Do NOT identify yourself as SurfSense or any other tool — you are DocuMentor."""

logger = logging.getLogger("hermes-service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s [%(funcName)s] %(message)s",
)

# Request ID for structured tracing
import uuid as _uuid

def _req_id() -> str:
    return _uuid.uuid4().hex[:8]

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

AGENT_POOL_SIZE = int(os.getenv("HERMES_POOL_SIZE", "3"))

app = FastAPI(title="Hermes Service", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Internal service — only bridge talks to this
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Agent pool — concurrent queries without serialization
# ---------------------------------------------------------------------------

_agent_executor = ThreadPoolExecutor(max_workers=AGENT_POOL_SIZE + 1, thread_name_prefix="hermes")
_agent_pool: asyncio.Queue["AIAgent"] = asyncio.Queue()
_pool_initialized = False
_pool_lock = asyncio.Lock()


def _create_agent(agent_id: int = 0) -> AIAgent:
    """Create a configured AIAgent instance."""
    try:
        from tools.mcp_tool import discover_mcp_tools
        tool_names = discover_mcp_tools()
        logger.info("agent-%d: MCP discovery found %d tools", agent_id, len(tool_names))
    except Exception as e:
        logger.warning("agent-%d: MCP tool rediscovery failed: %s", agent_id, e)

    agent = AIAgent(
        base_url=HERMES_BASE_URL,
        api_key=HERMES_API_KEY,
        model=HERMES_MODEL,
        max_iterations=HERMES_MAX_ITERATIONS,
        platform="web",
        enabled_toolsets=["mcp-documenter"],
        skip_context_files=True,
        skip_memory=True,
        quiet_mode=True,
        ephemeral_system_prompt=SYSTEM_PROMPT,
    )
    tool_count = len(agent.tools or [])
    logger.info(
        "agent-%d: created (model=%s, tools=%d)",
        agent_id, HERMES_MODEL, tool_count,
    )
    if tool_count == 0:
        logger.warning("agent-%d: ⚠️ No tools registered!", agent_id)
    return agent


async def _init_pool() -> None:
    """Initialize the agent pool (lazy, once)."""
    global _pool_initialized
    async with _pool_lock:
        if _pool_initialized:
            return
        loop = asyncio.get_running_loop()
        logger.info("Initializing agent pool (size=%d)...", AGENT_POOL_SIZE)
        for i in range(AGENT_POOL_SIZE):
            agent = await loop.run_in_executor(_agent_executor, _create_agent, i)
            await _agent_pool.put(agent)
        _pool_initialized = True
        logger.info("Agent pool ready (%d agents)", AGENT_POOL_SIZE)


class _AgentLease:
    """Context manager: borrow an agent from the pool, return it after."""

    def __init__(self):
        self.agent: Optional[AIAgent] = None

    async def __aenter__(self) -> AIAgent:
        await _init_pool()
        self.agent = await _agent_pool.get()
        return self.agent

    async def __aexit__(self, *exc):
        if self.agent is not None:
            await _agent_pool.put(self.agent)


def lease_agent() -> _AgentLease:
    """Borrow an agent from the pool. Usage: async with lease_agent() as agent: ..."""
    return _AgentLease()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    search_space_id: int = Field(default=1)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    thread_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Dashboard parser (same as bridge)
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(\{.*?\})\s*\n```", re.DOTALL)


def _parse_dashboard(text: str) -> Optional[dict]:
    """Try to extract a dashboard JSON block from the response text."""
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and "type" in data:
                return data
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# SSE query endpoint
# ---------------------------------------------------------------------------

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    """Run a query through Hermes AIAgent with SSE streaming."""

    rid = _req_id()
    logger.info("[%s] query: %.80s (space=%d)", rid, request.query, request.search_space_id)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    # Callbacks: push events into the async queue from the executor thread
    def on_stream_delta(delta: str | None) -> None:
        if delta is None:
            return
        asyncio.run_coroutine_threadsafe(
            queue.put({"event": "delta", "data": {"delta": delta}}),
            loop,
        )

    def on_tool_progress(tool_name: str, args_preview: str = "") -> None:
        asyncio.run_coroutine_threadsafe(
            queue.put({
                "event": "tool",
                "data": {"tool": tool_name, "status": "running", "preview": args_preview[:100]},
            }),
            loop,
        )

    def on_status(status_msg: str) -> None:
        asyncio.run_coroutine_threadsafe(
            queue.put({"event": "status", "data": {"message": status_msg}}),
            loop,
        )

    async def event_generator():
        """Generate SSE events from the queue. Agent is leased from pool."""
        agent_lease = lease_agent()
        agent = await agent_lease.__aenter__()
        t_start = time.time()

        try:
            # Set callbacks on the leased agent
            agent.stream_delta_callback = on_stream_delta
            agent.tool_progress_callback = on_tool_progress
            agent.status_callback = on_status

            def _run():
                try:
                    return agent.run_conversation(
                        user_message=request.query,
                        conversation_history=list(request.conversation_history),
                    )
                except Exception as e:
                    logger.exception("[%s] Agent error", rid)
                    return {"error": str(e)}

            task = loop.run_in_executor(_agent_executor, _run)

            # Stream events until the agent finishes
            while True:
                if task.done():
                    while not queue.empty():
                        item = await queue.get()
                        yield {
                            "event": item["event"],
                            "data": json.dumps(item["data"]),
                        }
                    break

                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield {
                        "event": item["event"],
                        "data": json.dumps(item["data"]),
                    }
                except asyncio.TimeoutError:
                    continue

            # Get the result
            try:
                result = await task
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)}),
                }
                return

            if "error" in result:
                logger.warning("[%s] query failed: %s", rid, result["error"])
                yield {
                    "event": "error",
                    "data": json.dumps({"error": result["error"]}),
                }
                return

            # Build final response
            final_response = result.get("final_response", "")
            messages = result.get("messages", [])
            dashboard = _parse_dashboard(final_response)
            if dashboard is None:
                dashboard = {"type": "summary", "content": final_response, "query": request.query}

            elapsed = time.time() - t_start
            logger.info("[%s] query complete (%.1fs, %d chars)", rid, elapsed, len(final_response))

            yield {
                "event": "done",
                "data": json.dumps({
                    "response": final_response,
                    "messages": messages,
                    "dashboard": dashboard,
                }),
            }

        finally:
            # Clear callbacks and return agent to pool
            agent.stream_delta_callback = None
            agent.tool_progress_callback = None
            agent.status_callback = None
            await agent_lease.__aexit__(None, None, None)

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "hermes-agent",
        "version": "0.5.0",
        "model": HERMES_MODEL,
        "pool_size": AGENT_POOL_SIZE,
        "pool_ready": _pool_initialized,
        "pool_available": _agent_pool.qsize() if _pool_initialized else 0,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Hermes Service v0.5.0 on port %s", HERMES_PORT)
    logger.info("Model: %s @ %s", HERMES_MODEL, HERMES_BASE_URL)
    logger.info("Agent pool size: %d", AGENT_POOL_SIZE)
    logger.info("MCP URL: %s", MCP_URL)
    uvicorn.run(app, host="0.0.0.0", port=HERMES_PORT, log_level="info")
