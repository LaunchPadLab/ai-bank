"""Anthropic tool surface + dispatch over the in-process ``Catalog``.

This is the single place that maps tool names to :class:`aibank_mcp.catalog.Catalog` methods.
``ANTHROPIC_TOOLS`` is a **static** module-level list -- it must never be rebuilt per request
or the prompt cache (which renders ``tools`` first) silently invalidates.

We expose a curated 7-tool subset of the MCP server's surface: the search -> get_* progressive
disclosure flow is preserved 1:1, the three ``list_*`` tools are collapsed into one
``list_catalog(kind=...)``, and ``catalog_overview``/``list_skill_references`` are dropped
(the overview lives in the cached system prompt; ``get_skill`` already returns reference
filenames). Fewer tools = a smaller cached prefix and less model confusion.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from aibank_mcp.catalog import Catalog

from .events import Source

# Static tool schemas. Descriptions are adapted from the MCP server's tool docstrings, which
# are already tuned for an LLM audience. Keep key order deterministic (cache stability).
ANTHROPIC_TOOLS: list[dict] = [
    {
        "name": "search",
        "description": (
            "Search the ai-bank catalog by keyword across skills, agents, and rules. Returns "
            "ranked summaries (name + description + score). Use this FIRST to discover relevant "
            "assets, then fetch full content with get_skill / get_agent / get_rule. Filter with "
            "`kind` to restrict to one asset type."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords to search for."},
                "kind": {
                    "type": "string",
                    "enum": ["all", "skill", "agent", "rule"],
                    "description": "Restrict results to one asset type (default: all).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 15).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_skill",
        "description": (
            "Get a skill's full SKILL.md body plus metadata, its reference filenames, and which "
            "agents use it. Call search or list_catalog(kind='skills') to discover names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The skill slug."}},
            "required": ["name"],
        },
    },
    {
        "name": "get_skill_reference",
        "description": (
            "Get the markdown body of one of a skill's reference files. `filename` accepts either "
            "'sessions' or 'sessions.md'. get_skill lists a skill's available reference filenames."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The skill slug."},
                "filename": {"type": "string", "description": "Reference filename."},
            },
            "required": ["name", "filename"],
        },
    },
    {
        "name": "get_agent",
        "description": (
            "Get an agent's full system prompt plus its resolved/unresolved skill cross-links. "
            "Call search or list_catalog(kind='agents') to discover names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The agent slug."}},
            "required": ["name"],
        },
    },
    {
        "name": "get_rule",
        "description": (
            "Get a coding-convention rule's full body and its path globs. Call "
            "list_catalog(kind='rules') or search to discover names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The rule slug."}},
            "required": ["name"],
        },
    },
    {
        "name": "get_rules_for_path",
        "description": (
            "Return the coding-convention rules that apply to a given file, with their bodies "
            "inline. Pass a REPO-RELATIVE path (e.g. 'app/models/user.rb'); the server matches it "
            "against each rule's path globs and adds the general (always-applicable) rules unless "
            "include_general is false."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Repo-relative file path, e.g. 'app/models/user.rb'.",
                },
                "include_general": {
                    "type": "boolean",
                    "description": "Include always-applicable rules (default true).",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_catalog",
        "description": (
            "List summaries of one asset type to browse what exists when search is too narrow "
            "(e.g. 'what skills cover testing?'). Returns name + description per asset."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["skills", "agents", "rules"],
                    "description": "Which asset type to list.",
                },
                "source": {
                    "type": "string",
                    "enum": ["all", "claude", "codex"],
                    "description": "For skills only: filter by origin (default all).",
                },
                "include_general": {
                    "type": "boolean",
                    "description": "For rules only: include always-applicable rules (default true).",
                },
            },
            "required": ["kind"],
        },
    },
]

# Human-readable activity labels for the frontend's "what the agent is doing" chips.
_TOOL_LABELS = {
    "search": lambda a: f"Searching the catalog for “{a.get('query', '')}”…",
    "get_skill": lambda a: f"Reading skill {a.get('name', '')}…",
    "get_skill_reference": lambda a: (
        f"Reading {a.get('name', '')} reference {a.get('filename', '')}…"
    ),
    "get_agent": lambda a: f"Reading agent {a.get('name', '')}…",
    "get_rule": lambda a: f"Reading rule {a.get('name', '')}…",
    "get_rules_for_path": lambda a: f"Looking up rules for {a.get('path', '')}…",
    "list_catalog": lambda a: f"Listing {a.get('kind', 'catalog')}…",
}


def tool_label(name: str, arguments: dict) -> str:
    """A short human-readable description of a tool call for the UI."""
    builder = _TOOL_LABELS.get(name)
    return builder(arguments or {}) if builder else f"Running {name}…"


@dataclass(frozen=True)
class ToolOutcome:
    """Result of executing one tool call."""

    content: str  # serialized result fed back to the model as a tool_result
    is_error: bool
    sources: tuple[Source, ...] = ()  # citable assets actually retrieved (empty for discovery)


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def execute_tool(catalog: Catalog, name: str, arguments: dict) -> ToolOutcome:
    """Run one tool against the catalog. Never raises -- a failure becomes an error result so
    the model can see it and self-correct rather than crashing the stream."""
    args = arguments or {}
    try:
        if name == "search":
            hits = catalog.search(
                str(args.get("query", "")),
                kind=str(args.get("kind", "all")),
                limit=int(args.get("limit", 15)),
            )
            return ToolOutcome(_dump([asdict(h) for h in hits]), False)

        if name == "list_catalog":
            return _list_catalog(catalog, args)

        if name == "get_skill":
            return _get_skill(catalog, str(args.get("name", "")))

        if name == "get_skill_reference":
            return _get_skill_reference(
                catalog, str(args.get("name", "")), str(args.get("filename", ""))
            )

        if name == "get_agent":
            return _get_agent(catalog, str(args.get("name", "")))

        if name == "get_rule":
            return _get_rule(catalog, str(args.get("name", "")))

        if name == "get_rules_for_path":
            return _get_rules_for_path(
                catalog,
                str(args.get("path", "")),
                include_general=bool(args.get("include_general", True)),
            )

        return ToolOutcome(f"Unknown tool {name!r}.", True)
    except Exception as exc:  # one bad call must not kill the stream
        return ToolOutcome(f"Tool error while running {name!r}: {exc}", True)


def _list_catalog(catalog: Catalog, args: dict) -> ToolOutcome:
    kind = str(args.get("kind", "")).lower()
    if kind == "skills":
        rows = catalog.list_skill_summaries(str(args.get("source", "all")))
    elif kind == "agents":
        rows = catalog.list_agent_summaries()
    elif kind == "rules":
        rows = catalog.list_rule_summaries(bool(args.get("include_general", True)))
    else:
        return ToolOutcome(
            f"Unknown kind {kind!r}. Use one of: skills, agents, rules.", True
        )
    return ToolOutcome(_dump([asdict(r) for r in rows]), False)


def _get_skill(catalog: Catalog, name: str) -> ToolOutcome:
    detail = catalog.skill_detail(name)
    if detail is None:
        return ToolOutcome(
            f"Unknown skill {name!r}. Use search or list_catalog(kind='skills') to find skills.",
            True,
        )
    return ToolOutcome(_dump(asdict(detail)), False, (Source("skill", detail.name),))


def _get_skill_reference(catalog: Catalog, name: str, filename: str) -> ToolOutcome:
    detail = catalog.skill_detail(name)
    if detail is None:
        return ToolOutcome(
            f"Unknown skill {name!r}. Use search or list_catalog(kind='skills') to find skills.",
            True,
        )
    body = catalog.read_skill_reference(name, filename)
    if body is None:
        available = [r.filename for r in detail.references]
        hint = ", ".join(available) if available else "(this skill has no reference files)"
        return ToolOutcome(
            f"Skill {detail.name!r} has no reference {filename!r}. Available: {hint}", True
        )
    # Resolve the canonical reference filename for a stable citation/link.
    wanted = filename.strip().lower()
    canonical = next(
        (r.filename for r in detail.references
         if wanted in (r.filename.lower(), r.filename.lower().removesuffix(".md"))),
        filename,
    )
    return ToolOutcome(body, False, (Source("skill", detail.name, canonical),))


def _get_agent(catalog: Catalog, name: str) -> ToolOutcome:
    detail = catalog.agent_detail(name)
    if detail is None:
        return ToolOutcome(
            f"Unknown agent {name!r}. Use search or list_catalog(kind='agents') to find agents.",
            True,
        )
    return ToolOutcome(_dump(asdict(detail)), False, (Source("agent", detail.name),))


def _get_rule(catalog: Catalog, name: str) -> ToolOutcome:
    detail = catalog.rule_detail(name)
    if detail is None:
        return ToolOutcome(
            f"Unknown rule {name!r}. Use list_catalog(kind='rules') or search to find rules.", True
        )
    return ToolOutcome(_dump(asdict(detail)), False, (Source("rule", detail.name),))


def _get_rules_for_path(catalog: Catalog, path: str, *, include_general: bool) -> ToolOutcome:
    result = catalog.rules_for_path(path, include_general)
    sources = [Source("rule", m.name) for m in result.matched]
    sources += [Source("rule", g.name) for g in result.general]
    return ToolOutcome(_dump(asdict(result)), False, tuple(sources))
