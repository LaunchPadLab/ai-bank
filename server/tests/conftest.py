"""Shared pytest fixtures.

Two content sources are used: a tiny synthetic tree (``tmp_kb``) for deterministic edge-case
tests, and the real ``claude/`` checkout (``repo_root``/``real_catalog``) for a smoke pass that
proves the loader handles the actual corpus.
"""

from pathlib import Path

import pytest

from aibank_mcp.catalog import build_catalog
from aibank_mcp.config import resolve_repo_root


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return resolve_repo_root()


@pytest.fixture(scope="session")
def real_catalog(repo_root):
    return build_catalog(repo_root)


@pytest.fixture
def tmp_kb(tmp_path: Path) -> Path:
    """Build a minimal ai-bank-shaped content tree and return its repo root."""
    root = tmp_path / "kb"

    # Skill with a singular reference/ dir, comma-string allowed-tools.
    _write(
        root / "claude/skills/good-skill/SKILL.md",
        "---\n"
        "name: good-skill\n"
        "description: Implements the good thing. Use when you need goodness.\n"
        "allowed-tools: Read, Write, Edit\n"
        "---\n\n# Good Skill\n\n## Setup\nDo the good thing.\n",
    )
    _write(root / "claude/skills/good-skill/reference/details.md", "# Details\nMore detail.\n")

    # Skill with a plural references/ dir and a folded block-scalar description.
    _write(
        root / "claude/skills/plural-skill/SKILL.md",
        "---\n"
        "name: plural-skill\n"
        "description: >-\n"
        "  Handles plural references. Use when testing\n"
        "  the references directory spelling.\n"
        "user-invocable: true\n"
        "---\n\n# Plural Skill\n",
    )
    _write(root / "claude/skills/plural-skill/references/template.md", "# Template\n")

    # Directory with no SKILL.md -> should produce a load warning, not a crash.
    (root / "claude/skills/broken-skill").mkdir(parents=True)

    # Agent that cross-links a known and an unknown skill; README must be skipped.
    _write(
        root / "claude/agents/test-agent.md",
        "---\n"
        "name: test-agent\n"
        "description: A test agent. Use for testing.\n"
        "model: inherit\n"
        "skills: [good-skill, ghost-skill]\n"
        "---\n\nYou are a test agent.\n",
    )
    _write(root / "claude/agents/README.md", "# Agents\nNot an agent.\n")

    # A path-scoped rule and a general (no-frontmatter) rule; README must be skipped.
    _write(
        root / "claude/rules/widgets.md",
        '---\npaths:\n  - "app/widgets/**/*.rb"\n---\n\n# Widget Conventions\nBe widgety.\n',
    )
    _write(root / "claude/rules/general-rule.md", "---\n---\n\n# General\nAlways applies.\n")
    _write(root / "claude/rules/README.md", "# Rules\nNot a rule.\n")

    # A codex render-only skill that should be merged into the catalog.
    _write(
        root / "codex/skills/render-deploy/SKILL.md",
        "---\nname: render-deploy\ndescription: Deploy to Render.\n---\n\n# Render Deploy\n",
    )
    # A codex skill NOT on the render allowlist -> must be ignored.
    _write(
        root / "codex/skills/codex-extra/SKILL.md",
        "---\nname: codex-extra\ndescription: Should not be merged.\n---\n\n# Extra\n",
    )

    # A command -> becomes an MCP prompt; exercises $ARGUMENTS substitution.
    _write(
        root / "claude/commands/echo-cmd.md",
        "---\nname: echo-cmd\ndescription: Echo the args.\n---\n\nEcho: $ARGUMENTS\n",
    )

    return root
