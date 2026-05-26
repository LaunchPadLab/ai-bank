"""MCP tool surface.

All tools are read-only, idempotent wrappers over :class:`~aibank_mcp.catalog.Catalog`.
They follow progressive disclosure: ``list_*``/``search`` return cheap summaries, ``get_*``
return full bodies. "Not found" raises :class:`ToolError` with a message pointing at the
companion discovery tool.
"""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from .catalog import Catalog
from .models import (
    AgentDetail,
    AgentSummary,
    CatalogOverview,
    ReferenceInfo,
    RuleDetail,
    RuleSummary,
    RulesForPathResult,
    SearchHit,
    SkillDetail,
    SkillSummary,
)

READONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def register(mcp: FastMCP, catalog: Catalog) -> None:
    """Register all read-only tools on ``mcp``, closing over ``catalog``."""

    @mcp.tool(annotations=READONLY)
    def search(
        query: str,
        kind: Literal["all", "skill", "agent", "rule"] = "all",
        limit: int = 15,
    ) -> list[SearchHit]:
        """Search the ai-bank catalog by keyword across skills, agents, and rules.

        Returns ranked summaries (name + description + score). Use this first to discover
        relevant assets, then fetch full content with get_skill / get_agent / get_rule.
        Filter with `kind` to restrict to one asset type.
        """
        return catalog.search(query, kind=kind, limit=limit)

    @mcp.tool(annotations=READONLY)
    def catalog_overview() -> CatalogOverview:
        """Summarize the catalog: asset counts, whether Render skills are included, and any
        load warnings. A cheap call for orientation and diagnostics."""
        return catalog.overview()

    # ---- skills ---------------------------------------------------------- #
    @mcp.tool(annotations=READONLY)
    def list_skills(source: Literal["all", "claude", "codex"] = "all") -> list[SkillSummary]:
        """List skill summaries (name, description, reference filenames). `source` filters by
        origin: "claude" (canonical) or "codex" (Render-only skills)."""
        return catalog.list_skill_summaries(source)

    @mcp.tool(annotations=READONLY)
    def get_skill(name: str) -> SkillDetail:
        """Get a skill's full SKILL.md body plus metadata, its reference files, and which
        agents use it. Call list_skills or search to discover names."""
        detail = catalog.skill_detail(name)
        if detail is None:
            raise ToolError(f"Unknown skill {name!r}. Use list_skills or search to find skills.")
        return detail

    @mcp.tool(annotations=READONLY)
    def list_skill_references(name: str) -> list[ReferenceInfo]:
        """List a skill's supporting reference files (filenames only). Fetch one with
        get_skill_reference."""
        infos = catalog.skill_reference_infos(name)
        if infos is None:
            raise ToolError(f"Unknown skill {name!r}. Use list_skills or search to find skills.")
        return infos

    @mcp.tool(annotations=READONLY)
    def get_skill_reference(name: str, filename: str) -> str:
        """Get the markdown body of one of a skill's reference files. `filename` accepts either
        "sessions" or "sessions.md"."""
        if not catalog.skill_exists(name):
            raise ToolError(f"Unknown skill {name!r}. Use list_skills or search to find skills.")
        body = catalog.read_skill_reference(name, filename)
        if body is None:
            available = [r.filename for r in (catalog.skill_reference_infos(name) or [])]
            hint = ", ".join(available) if available else "(this skill has no reference files)"
            raise ToolError(f"Skill {name!r} has no reference {filename!r}. Available: {hint}")
        return body

    # ---- agents ---------------------------------------------------------- #
    @mcp.tool(annotations=READONLY)
    def list_agents() -> list[AgentSummary]:
        """List agent summaries (name, description, model, linked skills)."""
        return catalog.list_agent_summaries()

    @mcp.tool(annotations=READONLY)
    def get_agent(name: str) -> AgentDetail:
        """Get an agent's full system prompt plus its resolved/unresolved skill cross-links.
        Call list_agents or search to discover names."""
        detail = catalog.agent_detail(name)
        if detail is None:
            raise ToolError(f"Unknown agent {name!r}. Use list_agents or search to find agents.")
        return detail

    # ---- rules ----------------------------------------------------------- #
    @mcp.tool(annotations=READONLY)
    def list_rules(include_general: bool = True) -> list[RuleSummary]:
        """List coding-convention rules with their path globs. General (always-applicable)
        rules have no globs; set include_general=False to omit them."""
        return catalog.list_rule_summaries(include_general)

    @mcp.tool(annotations=READONLY)
    def get_rule(name: str) -> RuleDetail:
        """Get a rule's full body and its path globs. Call list_rules to discover names."""
        detail = catalog.rule_detail(name)
        if detail is None:
            raise ToolError(f"Unknown rule {name!r}. Use list_rules to find rules.")
        return detail

    @mcp.tool(annotations=READONLY)
    def get_rules_for_path(path: str, include_general: bool = True) -> RulesForPathResult:
        """Return the coding-convention rules that apply to a given file, with their bodies
        inline. Pass a REPO-RELATIVE path (e.g. "app/models/user.rb"); the server matches it
        against each rule's path globs and always adds the general rules (unless
        include_general=False). Call this before editing a file to learn the conventions."""
        return catalog.rules_for_path(path, include_general)
