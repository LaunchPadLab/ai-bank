"""Locate the ai-bank content and guard filesystem access.

The server reads ``<repo_root>/claude/{skills,agents,rules,commands}`` and, optionally,
the Render-only skills under ``<repo_root>/codex/skills``. ``resolve_repo_root`` finds the
repo whether the server runs from inside a checkout (local stdio) or is installed elsewhere
and pointed at content via ``AIBANK_REPO_ROOT``.
"""

from __future__ import annotations

import os
from pathlib import Path

# Layout constants (claude/ is the canonical source of truth; codex/ is transposed from it).
CLAUDE_DIR = "claude"
CODEX_DIR = "codex"
SKILLS_SUBDIR = "skills"
AGENTS_SUBDIR = "agents"
RULES_SUBDIR = "rules"
COMMANDS_SUBDIR = "commands"

ENV_REPO_ROOT = "AIBANK_REPO_ROOT"

# A directory is the ai-bank repo root iff it contains BOTH of these.
_MARKERS = (f"{CLAUDE_DIR}/{SKILLS_SUBDIR}", f"{CLAUDE_DIR}/{RULES_SUBDIR}")


def _is_repo_root(path: Path) -> bool:
    return all((path / marker).is_dir() for marker in _MARKERS)


def _walk_up(start: Path):
    start = start.resolve()
    yield from (start, *start.parents)


def resolve_repo_root(explicit: str | os.PathLike | None = None) -> Path:
    """Resolve the ai-bank repo root.

    Precedence: ``explicit`` arg (CLI ``--repo-root``) > ``$AIBANK_REPO_ROOT`` >
    auto-detect by walking up from this file and from the current working directory,
    looking for a dir that contains both ``claude/skills`` and ``claude/rules``.

    Raises ``FileNotFoundError`` with an actionable message if none qualifies.
    """
    explicit = explicit or os.environ.get(ENV_REPO_ROOT)
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not _is_repo_root(root):
            raise FileNotFoundError(
                f"{ENV_REPO_ROOT}/--repo-root points at {root}, which is not an ai-bank "
                f"checkout (expected {CLAUDE_DIR}/{SKILLS_SUBDIR} and "
                f"{CLAUDE_DIR}/{RULES_SUBDIR} inside it)."
            )
        return root

    searched: list[Path] = []
    for start in (Path(__file__).parent, Path.cwd()):
        for candidate in _walk_up(start):
            searched.append(candidate)
            if _is_repo_root(candidate):
                return candidate

    hint = "\n  ".join(dict.fromkeys(str(p) for p in searched))  # dedupe, keep order
    raise FileNotFoundError(
        "Could not locate the ai-bank repo (a directory containing "
        f"{CLAUDE_DIR}/{SKILLS_SUBDIR} and {CLAUDE_DIR}/{RULES_SUBDIR}).\n"
        f"Set {ENV_REPO_ROOT} or pass --repo-root. Searched upward from:\n  {hint}"
    )


def within_root(root: Path, candidate: Path) -> bool:
    """True if ``candidate`` resolves to a path inside ``root`` (path-traversal guard)."""
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
