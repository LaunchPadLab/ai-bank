"""FastAPI application: chat streaming endpoint, in-app asset viewer, and static frontend.

One process-wide :class:`Catalog` (immutable, safe for concurrent reads) and one shared
``AsyncAnthropic`` client back every request. The system prompt is built once at startup so its
bytes stay identical across requests (prompt-cache stability). The chat endpoint streams Server-
Sent Events; the asset endpoints reuse the same catalog the agent does, so citations resolve to
in-app pages without leaving the authenticated origin.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from aibank_mcp.catalog import build_catalog

from .agent import AgentLoop
from .config import ChatSettings
from .events import DoneEvent, ErrorEvent, to_sse
from .prompts import build_system_prompt

logger = logging.getLogger("aibank_web")

STATIC_DIR = Path(__file__).parent / "web" / "static"
_SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


def build_app(settings: ChatSettings) -> FastAPI:
    """Construct the FastAPI app. Catalog + system prompt are built here (once); the async
    Anthropic client lives for the app's lifespan."""
    catalog = build_catalog(settings.repo_root, include_render_skills=settings.include_render_skills)
    system_blocks = build_system_prompt(catalog)
    for w in catalog.load_warnings:
        logger.warning("content load warning: %s -> %s", w.path, w.reason)
    logger.info(
        "ai-bank chat: %d skills, %d agents, %d rules loaded from %s",
        len(catalog.skills), len(catalog.agents), len(catalog.rules), settings.repo_root,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = anthropic.AsyncAnthropic() if ChatSettings.api_key() else None
        if client is None:
            logger.error(
                "ANTHROPIC_API_KEY is not set: the chat endpoint will return an error. "
                "Asset browsing and the catalog API still work."
            )
        app.state.client = client
        try:
            yield
        finally:
            if client is not None:
                await client.close()

    app = FastAPI(title="ai-bank assistant", lifespan=lifespan)
    app.state.catalog = catalog
    app.state.settings = settings
    app.state.system_blocks = system_blocks

    _register_routes(app)
    if STATIC_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
    return app


def _register_routes(app: FastAPI) -> None:
    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/catalog/overview")
    async def overview(request: Request) -> dict:
        o = request.app.state.catalog.overview()
        return {"skills": o.skills, "agents": o.agents, "rules": o.rules}

    @app.get("/api/catalog/names")
    async def names(request: Request) -> dict:
        c = request.app.state.catalog
        return {"skills": c.skill_names(), "agents": c.agent_names(), "rules": c.rule_names()}

    @app.get("/api/asset/skill/{name}/reference/{filename}")
    async def asset_skill_reference(name: str, filename: str, request: Request):
        catalog = request.app.state.catalog
        if not catalog.skill_exists(name):
            return _not_found("skill", name)
        body = catalog.read_skill_reference(name, filename)
        if body is None:
            return JSONResponse({"error": f"No reference {filename!r} for skill {name!r}."}, 404)
        detail = catalog.skill_detail(name)
        return {"kind": "skill", "name": detail.name, "reference": filename, "body": body}

    @app.get("/api/asset/{kind}/{name}")
    async def asset_detail(kind: str, name: str, request: Request):
        catalog = request.app.state.catalog
        getters = {
            "skill": catalog.skill_detail,
            "agent": catalog.agent_detail,
            "rule": catalog.rule_detail,
        }
        getter = getters.get(kind)
        if getter is None:
            return JSONResponse({"error": f"Unknown asset kind {kind!r}."}, 404)
        detail = getter(name)
        if detail is None:
            return _not_found(kind, name)
        return {"kind": kind, **dataclasses.asdict(detail)}

    @app.post("/api/chat")
    async def chat(req: ChatRequest, request: Request) -> EventSourceResponse:
        settings: ChatSettings = request.app.state.settings
        client = request.app.state.client
        catalog = request.app.state.catalog
        system_blocks = request.app.state.system_blocks

        history = req.history[-settings.max_history :] if settings.max_history else []
        messages = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": req.message})

        async def event_stream() -> AsyncIterator[dict]:
            if client is None:
                yield to_sse(ErrorEvent("not_configured", "The assistant is not configured "
                                        "(missing ANTHROPIC_API_KEY)."))
                yield to_sse(DoneEvent())
                return
            loop = AgentLoop(client, catalog, settings, system_blocks)
            async for ev in loop.run(messages, is_disconnected=request.is_disconnected):
                yield to_sse(ev)

        return EventSourceResponse(event_stream(), headers=_SSE_HEADERS, ping=15)

    # ---- HTML shells (the SPA reads kind/name from the path) ---------------- #
    @app.get("/")
    async def index():
        return _page("index.html")

    @app.get("/a/skill/{name}/reference/{filename}")
    async def asset_reference_page(name: str, filename: str):
        return _page("asset.html")

    @app.get("/a/{kind}/{name}")
    async def asset_page(kind: str, name: str):
        return _page("asset.html")


def _page(filename: str):
    path = STATIC_DIR / filename
    if not path.is_file():
        return JSONResponse({"error": "Frontend assets not found."}, 404)
    return FileResponse(path)


def _not_found(kind: str, name: str) -> JSONResponse:
    return JSONResponse({"error": f"Unknown {kind} {name!r}."}, 404)
