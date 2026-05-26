"""Scan the ai-bank content tree into in-memory records.

Each loader is a pure function returning ``(records, warnings)``. A single malformed file
never aborts a load: it is recorded as a :class:`~aibank_mcp.models.LoadWarning` and skipped,
so the server still starts and ``catalog_overview`` can surface the problem.
"""

from __future__ import annotations

from pathlib import Path

from .frontmatter import read_markdown_with_frontmatter
from .models import Agent, LoadWarning, ReferenceFile, Rule, Skill

# The 5 skills that exist only under codex/skills (the Render deployment track).
RENDER_ONLY_SKILL_NAMES = frozenset(
    {
        "render-debug",
        "render-deploy",
        "render-migrate-from-heroku",
        "render-monitor",
        "render-workflows",
    }
)

# Supporting-docs dir spelling is inconsistent across skills; check both, prefer "reference".
_REFERENCE_DIR_NAMES = ("reference", "references")

# Files in agents/ and rules/ that are documentation, not assets.
_SKIP_FILE_NAMES = {"README.md"}


def _as_list(value, sep: str = ",") -> list[str]:
    """Normalize a frontmatter value to a list of non-empty strings.

    Handles parser output that may be a real list (block/inline YAML lists) or a scalar
    string (e.g. ``allowed-tools: Read, Write, Edit`` arrives as one comma-joined string).
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(sep) if part.strip()]


def _bool_or_none(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _detect_reference_dir(skill_dir: Path) -> str | None:
    for name in _REFERENCE_DIR_NAMES:
        if (skill_dir / name).is_dir():
            return name
    return None


def load_skills(skills_dir: Path, source: str = "claude") -> tuple[list[Skill], list[LoadWarning]]:
    """Load skills from a ``skills/`` directory (each skill is a dir containing SKILL.md)."""
    skills: list[Skill] = []
    warnings: list[LoadWarning] = []
    if not skills_dir.is_dir():
        return skills, warnings

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue  # structurally skips README.md and dotdirs
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            warnings.append(LoadWarning(str(entry), "directory has no SKILL.md"))
            continue
        try:
            meta, body = read_markdown_with_frontmatter(skill_md)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            warnings.append(LoadWarning(str(skill_md), f"parse error: {exc}"))
            continue

        name = _str_or_none(meta.get("name")) or entry.name
        description = _str_or_none(meta.get("description")) or ""
        if not description:
            warnings.append(LoadWarning(str(skill_md), "missing description"))

        ref_dir = _detect_reference_dir(entry)
        references: list[ReferenceFile] = []
        if ref_dir:
            for ref in sorted((entry / ref_dir).glob("*.md")):
                references.append(
                    ReferenceFile(
                        filename=ref.name,
                        rel_path=f"{ref_dir}/{ref.name}",
                        abs_path=str(ref.resolve()),
                    )
                )

        skills.append(
            Skill(
                name=name,
                description=description,
                source=source,
                allowed_tools=tuple(_as_list(meta.get("allowed-tools"))),
                user_invocable=_bool_or_none(meta.get("user-invocable")),
                disable_model_invocation=_bool_or_none(meta.get("disable-model-invocation")),
                argument_hint=_str_or_none(meta.get("argument-hint")),
                context=_str_or_none(meta.get("context")),
                agent=_str_or_none(meta.get("agent")),
                reference_dir=ref_dir,
                references=tuple(references),
                dir_path=str(entry.resolve()),
                body=body,
            )
        )
    return skills, warnings


def load_agents(agents_dir: Path) -> tuple[list[Agent], list[LoadWarning]]:
    """Load agents from an ``agents/`` directory (each agent is a ``*.md`` file)."""
    agents: list[Agent] = []
    warnings: list[LoadWarning] = []
    if not agents_dir.is_dir():
        return agents, warnings

    for path in sorted(agents_dir.glob("*.md")):  # glob("*.md") ignores the scripts/ subdir
        if path.name in _SKIP_FILE_NAMES:
            continue
        try:
            meta, body = read_markdown_with_frontmatter(path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(LoadWarning(str(path), f"parse error: {exc}"))
            continue

        agents.append(
            Agent(
                name=_str_or_none(meta.get("name")) or path.stem,
                description=_str_or_none(meta.get("description")) or "",
                model=_str_or_none(meta.get("model")),
                skills=tuple(_as_list(meta.get("skills"))),
                permission_mode=_str_or_none(meta.get("permissionMode")),
                disallowed_tools=tuple(_as_list(meta.get("disallowedTools"))),
                max_turns=_int_or_none(meta.get("maxTurns")),
                memory=_str_or_none(meta.get("memory")),
                background=_bool_or_none(meta.get("background")),
                isolation=_str_or_none(meta.get("isolation")),
                file_path=str(path.resolve()),
                body=body,
            )
        )
    return agents, warnings


def load_rules(rules_dir: Path) -> tuple[list[Rule], list[LoadWarning]]:
    """Load rules from a ``rules/`` directory (each rule is a ``*.md`` file)."""
    rules: list[Rule] = []
    warnings: list[LoadWarning] = []
    if not rules_dir.is_dir():
        return rules, warnings

    for path in sorted(rules_dir.glob("*.md")):  # glob("*.md") ignores the scripts/ subdir
        if path.name in _SKIP_FILE_NAMES:
            continue
        try:
            meta, body = read_markdown_with_frontmatter(path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(LoadWarning(str(path), f"parse error: {exc}"))
            continue

        paths = tuple(_as_list(meta.get("paths")))
        rules.append(
            Rule(
                name=path.stem,
                paths=paths,
                is_general=not paths,
                description=_str_or_none(meta.get("description")),
                file_path=str(path.resolve()),
                body=body,
            )
        )
    return rules, warnings
