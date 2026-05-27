"""Configuration for the ai-bank chat web app.

Follows the same conventions as ``aibank_mcp``: configuration comes from environment
variables (``AIBANK_WEB_*`` for app settings, the shared ``AIBANK_*`` for catalog location),
and the only secret -- ``ANTHROPIC_API_KEY`` -- is read from the environment, never a CLI
flag (so it can't leak via the process list). The Anthropic SDK reads ``ANTHROPIC_API_KEY``
on its own; we validate its presence at startup and fail fast with a clear message.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from aibank_mcp.config import resolve_repo_root

# Env var names (AIBANK_WEB_* for this app; AIBANK_* are shared with the MCP server).
ENV_MODEL = "AIBANK_WEB_MODEL"
ENV_EFFORT = "AIBANK_WEB_EFFORT"
ENV_MAX_TOKENS = "AIBANK_WEB_MAX_TOKENS"
ENV_MAX_ITERATIONS = "AIBANK_WEB_MAX_ITERATIONS"
ENV_REQUEST_TIMEOUT = "AIBANK_WEB_REQUEST_TIMEOUT"
ENV_MAX_HISTORY = "AIBANK_WEB_MAX_HISTORY"
ENV_HOST = "AIBANK_WEB_HOST"
ENV_PORT = "AIBANK_WEB_PORT"
ENV_LOG_LEVEL = "AIBANK_WEB_LOG_LEVEL"
ENV_API_KEY = "ANTHROPIC_API_KEY"  # read from env only, never a flag
ENV_INCLUDE_RENDER = "AIBANK_INCLUDE_RENDER"  # shared with the MCP server

DEFAULT_MODEL = "claude-opus-4-7"
# Effort levels accepted by Opus 4.7's output_config (low|medium|high|xhigh|max).
_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def _bool_env(name: str, default: bool) -> bool:
    """Mirror aibank_mcp.cli._bool_env so MCP and web read flags identically."""
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() not in {"0", "false", "no", "off", ""}


def _int_env(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None or not val.strip():
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass(frozen=True)
class ChatSettings:
    """Immutable settings snapshot built once at startup."""

    repo_root: Path
    model: str = DEFAULT_MODEL
    effort: str = "high"
    max_tokens: int = 16000
    max_iterations: int = 8
    request_timeout: int = 120  # wall-clock seconds per chat request
    max_history: int = 20  # cap client-supplied prior turns
    include_render_skills: bool = True
    host: str = "127.0.0.1"
    port: int = 8001  # distinct from the MCP server's 8000 so both run side by side
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, *, repo_root: str | os.PathLike | None = None) -> "ChatSettings":
        """Build settings from the environment, resolving the catalog location.

        ``repo_root`` overrides ``AIBANK_REPO_ROOT``/auto-detection when provided.
        Raises ``FileNotFoundError`` (via ``resolve_repo_root``) if the catalog can't be found.
        """
        effort = os.environ.get(ENV_EFFORT, "high").strip().lower()
        if effort not in _EFFORT_LEVELS:
            effort = "high"
        return cls(
            repo_root=resolve_repo_root(repo_root),
            model=os.environ.get(ENV_MODEL, DEFAULT_MODEL),
            effort=effort,
            max_tokens=_int_env(ENV_MAX_TOKENS, 16000),
            max_iterations=max(1, _int_env(ENV_MAX_ITERATIONS, 8)),
            request_timeout=max(1, _int_env(ENV_REQUEST_TIMEOUT, 120)),
            max_history=max(0, _int_env(ENV_MAX_HISTORY, 20)),
            include_render_skills=_bool_env(ENV_INCLUDE_RENDER, default=True),
            host=os.environ.get(ENV_HOST, "127.0.0.1"),
            port=_int_env(ENV_PORT, 8001),
            log_level=os.environ.get(ENV_LOG_LEVEL, "INFO").upper(),
        )

    @staticmethod
    def api_key() -> str | None:
        """The Anthropic API key from the environment (the SDK reads it the same way)."""
        key = os.environ.get(ENV_API_KEY)
        return key.strip() if key else None
