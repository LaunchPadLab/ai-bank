"""MCP resource surface — a URI-addressable mirror of a subset of the catalog.

Resources complement the tools for clients that support them (e.g. ``@``-mentions). Every
capability here is also reachable via tools, since resource support varies across clients.
Each function is a thin delegate to the same :class:`~aibank_mcp.catalog.Catalog` methods the
tools use, so there is a single source of truth.
"""

from __future__ import annotations

import dataclasses

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError

from .catalog import Catalog


def register(mcp: FastMCP, catalog: Catalog) -> None:
    """Register read-only resources on ``mcp``, closing over ``catalog``."""

    @mcp.resource("aibank://skills", mime_type="application/json")
    def skills_index() -> list[dict]:
        return [dataclasses.asdict(s) for s in catalog.list_skill_summaries()]

    @mcp.resource("aibank://agents", mime_type="application/json")
    def agents_index() -> list[dict]:
        return [dataclasses.asdict(a) for a in catalog.list_agent_summaries()]

    @mcp.resource("aibank://rules", mime_type="application/json")
    def rules_index() -> list[dict]:
        return [dataclasses.asdict(r) for r in catalog.list_rule_summaries()]

    @mcp.resource("aibank://skill/{name}", mime_type="text/markdown")
    def skill_body(name: str) -> str:
        detail = catalog.skill_detail(name)
        if detail is None:
            raise ResourceError(f"Unknown skill {name!r}")
        return detail.body

    @mcp.resource("aibank://agent/{name}", mime_type="text/markdown")
    def agent_body(name: str) -> str:
        detail = catalog.agent_detail(name)
        if detail is None:
            raise ResourceError(f"Unknown agent {name!r}")
        return detail.body

    @mcp.resource("aibank://rule/{name}", mime_type="text/markdown")
    def rule_body(name: str) -> str:
        detail = catalog.rule_detail(name)
        if detail is None:
            raise ResourceError(f"Unknown rule {name!r}")
        return detail.body

    @mcp.resource("aibank://skill/{name}/reference/{filename*}", mime_type="text/markdown")
    def skill_reference(name: str, filename: str) -> str:
        if not catalog.skill_exists(name):
            raise ResourceError(f"Unknown skill {name!r}")
        body = catalog.read_skill_reference(name, filename)
        if body is None:
            raise ResourceError(f"Skill {name!r} has no reference {filename!r}")
        return body
