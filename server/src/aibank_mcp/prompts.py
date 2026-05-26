"""Optional MCP prompt surface — exposes the ``claude/commands/*.md`` as prompts.

User-invoked prompt templates, separate from the Skills/Agents/Rules core. We only ever
*return* the command text (substituting ``$ARGUMENTS`` when present), never execute it, so
this stays read-only. Registration is best-effort: a malformed command is skipped, not fatal.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastmcp import FastMCP

from .config import CLAUDE_DIR, COMMANDS_SUBDIR
from .frontmatter import read_markdown_with_frontmatter

logger = logging.getLogger("aibank_mcp")


def _derive_description(meta: dict, body: str, name: str) -> str:
    described = meta.get("description")
    if described:
        return str(described)
    for line in body.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped if len(stripped) <= 140 else stripped[:139] + "…"
    return f"ai-bank command: {name}"


def _make_render(body: str):
    def render(arguments: str = "") -> str:
        """Render this command, substituting $ARGUMENTS with the provided text."""
        return body.replace("$ARGUMENTS", arguments)

    return render


def register(mcp: FastMCP, repo_root: Path) -> int:
    """Register each command as a prompt. Returns the number registered."""
    commands_dir = repo_root / CLAUDE_DIR / COMMANDS_SUBDIR
    if not commands_dir.is_dir():
        return 0

    count = 0
    for path in sorted(commands_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            meta, body = read_markdown_with_frontmatter(path)
            name = str(meta.get("name") or path.stem)
            description = _derive_description(meta, body, name)
            render = _make_render(body)
            render.__name__ = name.replace("-", "_")
            mcp.prompt(name=name, description=description)(render)
            count += 1
        except Exception as exc:  # noqa: BLE001 - one bad command must not break startup
            logger.warning("skipping command prompt %s: %s", path, exc)
    return count
