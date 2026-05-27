"""Command-line entry point for the chat web app.

Mirrors ``aibank_mcp.cli``: resolve the repo root, build the app once, run uvicorn. Config comes
from the environment (``AIBANK_WEB_*`` / shared ``AIBANK_*``); CLI flags override host/port/
repo-root/log-level. The Anthropic API key is read from ``ANTHROPIC_API_KEY`` by the SDK -- never
a flag, so it can't leak via the process list.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .config import (
    ENV_HOST,
    ENV_LOG_LEVEL,
    ENV_PORT,
    ChatSettings,
)
from .config import (
    resolve_repo_root as _resolve_repo_root,  # re-exported from aibank_mcp.config
)

logger = logging.getLogger("aibank_web")

ENV_REPO_ROOT = "AIBANK_REPO_ROOT"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aibank-web",
        description="Web chat app for the ai-bank Skills/Agents/Rules knowledge base.",
    )
    p.add_argument("--host", default=os.environ.get(ENV_HOST, "127.0.0.1"),
                   help="HTTP bind host (default: 127.0.0.1; env %s)." % ENV_HOST)
    p.add_argument("--port", type=int, default=int(os.environ.get(ENV_PORT, "8001")),
                   help="HTTP bind port (default: 8001; env %s)." % ENV_PORT)
    p.add_argument("--repo-root", default=os.environ.get(ENV_REPO_ROOT),
                   help="Path to the ai-bank checkout (env %s; auto-detected otherwise)."
                        % ENV_REPO_ROOT)
    p.add_argument("--log-level", default=os.environ.get(ENV_LOG_LEVEL, "INFO"),
                   help="Logging level (default: INFO; env %s)." % ENV_LOG_LEVEL)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        repo_root = _resolve_repo_root(args.repo_root)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    # CLI flags win over env for host/port; the rest comes from the environment.
    os.environ[ENV_HOST] = args.host
    os.environ[ENV_PORT] = str(args.port)
    settings = ChatSettings.from_env(repo_root=repo_root)

    if ChatSettings.api_key() is None:
        logger.error(
            "ANTHROPIC_API_KEY is not set. The app will start and serve catalog/asset pages, "
            "but the chat endpoint will return an error until the key is provided."
        )

    # Imported here so `aibank-web --help` doesn't require the optional web deps to be installed.
    import uvicorn

    from .app import build_app

    app = build_app(settings)
    logger.info("starting ai-bank chat on http://%s:%d (model=%s, effort=%s)",
                settings.host, settings.port, settings.model, settings.effort)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=args.log_level.lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
