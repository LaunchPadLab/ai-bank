"""Assemble the FastMCP server from the catalog + tool/resource/prompt registrations.

``build_server`` is transport-agnostic: it constructs the server and its read-only surface
but does not choose stdio vs HTTP. ``cli.main`` makes that choice. Keeping them separate lets
tests drive the server in-memory via ``fastmcp.Client(build_server(root))``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastmcp import FastMCP

from . import prompts as _prompts
from . import resources as _resources
from . import tools as _tools
from .catalog import build_catalog

logger = logging.getLogger("aibank_mcp")

INSTRUCTIONS = (
    "ai-bank exposes a read-only catalog of reusable AI-tooling assets for Rails/Hotwire "
    "development: Skills (instructional SKILL.md packages + reference docs), Agents (specialist "
    "system prompts), and Rules (path-scoped coding conventions).\n\n"
    "Start with `search` to discover assets, then fetch full content with `get_skill`, "
    "`get_agent`, or `get_rule`. Before editing a file, call `get_rules_for_path` with the "
    "repo-relative path to learn which conventions apply."
)


def build_server(
    repo_root: Path,
    *,
    include_render_skills: bool = True,
    register_resources: bool = True,
    register_prompts: bool = True,
    auth=None,
) -> FastMCP:
    """Build the ai-bank FastMCP server with content loaded from ``repo_root``."""
    catalog = build_catalog(repo_root, include_render_skills=include_render_skills)

    mcp = FastMCP(name="ai-bank", instructions=INSTRUCTIONS, auth=auth)
    _tools.register(mcp, catalog)
    if register_resources:
        _resources.register(mcp, catalog)
    n_prompts = _prompts.register(mcp, repo_root) if register_prompts else 0

    logger.info(
        "ai-bank catalog loaded from %s: %d skills, %d agents, %d rules, %d prompts (%d warnings)",
        repo_root,
        len(catalog.skills),
        len(catalog.agents),
        len(catalog.rules),
        n_prompts,
        len(catalog.load_warnings),
    )
    for warning in catalog.load_warnings:
        logger.warning("content load warning: %s -> %s", warning.path, warning.reason)

    return mcp
