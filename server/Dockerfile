# syntax=docker/dockerfile:1
#
# Container image for the ai-bank MCP server (read-only, HTTP transport).
#
# The build context MUST be the repo root so the catalog content (claude/, codex/) is
# included in the image:
#
#   docker build -f server/Dockerfile -t aibank-mcp .
#
# It binds 0.0.0.0:8000 with AIBANK_MCP_ALLOW_INSECURE_HTTP=1 on the assumption that an
# authenticating proxy (e.g. Cloudflare Access) terminates auth in front of it. Do NOT publish
# this port to an untrusted network without such a proxy. See deploy/cloudflare-access.md.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the server package first so editing catalog content doesn't bust the dependency layer.
# The [web] extra adds the chat web app's deps (anthropic, fastapi, uvicorn). The image bundles
# BOTH the `aibank-mcp` and `aibank-web` console scripts; docker-compose picks which to run per
# service. Static frontend assets ship as package data under src/aibank_web/web/static/.
COPY server/ /app/server/
RUN pip install "/app/server[web]"

# Catalog content, read at runtime (claude/ is canonical; codex/ supplies the Render skills).
COPY claude/ /app/claude/
COPY codex/ /app/codex/

# Run unprivileged.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV AIBANK_REPO_ROOT=/app \
    AIBANK_MCP_TRANSPORT=http \
    AIBANK_MCP_HOST=0.0.0.0 \
    AIBANK_MCP_PORT=8000 \
    AIBANK_MCP_ALLOW_INSECURE_HTTP=1

EXPOSE 8000

# Liveness: confirm the server is accepting TCP connections on its port.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8000), 3).close()"]

CMD ["aibank-mcp"]
