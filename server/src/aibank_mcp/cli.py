"""Command-line entry point and transport selection.

Selects stdio (default) or streamable HTTP. Logging goes to **stderr only** — stdout is
reserved for JSON-RPC framing under the stdio transport, and any stray stdout write corrupts
the protocol.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .config import ENV_REPO_ROOT, resolve_repo_root
from .server import build_server

logger = logging.getLogger("aibank_mcp")

ENV_TRANSPORT = "AIBANK_MCP_TRANSPORT"
ENV_HOST = "AIBANK_MCP_HOST"
ENV_PORT = "AIBANK_MCP_PORT"
ENV_PATH = "AIBANK_MCP_PATH"
ENV_LOG_LEVEL = "AIBANK_MCP_LOG_LEVEL"
ENV_TOKEN = "AIBANK_MCP_TOKEN"  # read from env, never a flag (avoids leaking via process list)
ENV_INCLUDE_RENDER = "AIBANK_INCLUDE_RENDER"


def _is_loopback(host: str) -> bool:
    h = host.strip().lower()
    return h in {"127.0.0.1", "::1", "localhost"} or h.startswith("127.")


def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() not in {"0", "false", "no", "off", ""}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aibank-mcp",
        description="Read-only MCP server for the ai-bank Skills/Agents/Rules knowledge base.",
    )
    p.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=os.environ.get(ENV_TRANSPORT, "stdio"),
        help="Transport to serve on (default: stdio; env %s)." % ENV_TRANSPORT,
    )
    p.add_argument("--host", default=os.environ.get(ENV_HOST, "127.0.0.1"),
                   help="HTTP bind host (default: 127.0.0.1; env %s)." % ENV_HOST)
    p.add_argument("--port", type=int, default=int(os.environ.get(ENV_PORT, "8000")),
                   help="HTTP bind port (default: 8000; env %s)." % ENV_PORT)
    p.add_argument("--path", default=os.environ.get(ENV_PATH, "/mcp"),
                   help="HTTP endpoint path (default: /mcp; env %s)." % ENV_PATH)
    p.add_argument("--repo-root", default=os.environ.get(ENV_REPO_ROOT),
                   help="Path to the ai-bank checkout (env %s; auto-detected otherwise)." % ENV_REPO_ROOT)
    p.add_argument("--log-level", default=os.environ.get(ENV_LOG_LEVEL, "INFO"),
                   help="Logging level (default: INFO; env %s)." % ENV_LOG_LEVEL)
    p.add_argument("--no-render-skills", action="store_true",
                   help="Exclude the codex-only Render skills (also via %s=0)." % ENV_INCLUDE_RENDER)
    return p


def _make_auth(token: str):
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

    return StaticTokenVerifier(tokens={token: {"client_id": "aibank-mcp", "scopes": []}})


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        repo_root = resolve_repo_root(args.repo_root)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    include_render = _bool_env(ENV_INCLUDE_RENDER, default=True) and not args.no_render_skills
    token = os.environ.get(ENV_TOKEN)

    auth = None
    if args.transport == "http":
        if token:
            auth = _make_auth(token)
        elif not _is_loopback(args.host):
            logger.error(
                "Refusing to start HTTP transport on non-loopback host %r without authentication. "
                "Set %s to require a bearer token, bind to 127.0.0.1, or front the server with an "
                "authenticating reverse proxy.",
                args.host,
                ENV_TOKEN,
            )
            return 2

    mcp = build_server(repo_root, include_render_skills=include_render, auth=auth)

    if args.transport == "stdio":
        logger.info("starting ai-bank MCP server on stdio")
        mcp.run(show_banner=False)  # show_banner=False keeps stdout clean for JSON-RPC
    else:
        logger.info(
            "starting ai-bank MCP server on http://%s:%d%s (auth=%s)",
            args.host,
            args.port,
            args.path,
            "on" if auth else "off",
        )
        mcp.run(transport="http", host=args.host, port=args.port, path=args.path, show_banner=False)
    return 0
