"""ai-bank chat web app.

A FastAPI app that lets people ask natural-language questions about the ai-bank catalog.
A server-side Claude agent answers strictly from the catalog (Skills/Agents/Rules) and cites
its sources. It reuses the in-process :class:`aibank_mcp.catalog.Catalog` directly -- no network
hop to the MCP server, no duplicate retrieval logic.
"""

from __future__ import annotations

__version__ = "0.1.0"
