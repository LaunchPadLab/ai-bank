#!/usr/bin/env python3
"""Audit Claude-to-Codex transposition coverage."""

import sys
import tomllib
from pathlib import Path

from codex_transpose import parse_frontmatter


def claude_agent_names(root):
    names = set()
    for path in root.glob("agents/*.md"):
        if path.name == "README.md":
            continue
        metadata, _body = parse_frontmatter(path.read_text())
        names.add(metadata.get("name", path.stem))
    return names


def codex_agent_names(root):
    names = set()
    for path in root.glob("agents/*.toml"):
        names.add(tomllib.loads(path.read_text()).get("name"))
    return names


def claude_skill_names(root):
    names = set()
    for path in root.glob("skills/*/SKILL.md"):
        metadata, _body = parse_frontmatter(path.read_text())
        names.add(metadata.get("name", path.parent.name))
    return names


def codex_skill_names(root):
    names = set()
    for path in root.glob("skills/*/SKILL.md"):
        metadata, _body = parse_frontmatter(path.read_text())
        names.add(metadata.get("name", path.parent.name))
    return names


def claude_rule_paths(root):
    return {
        path.as_posix()
        for path in root.glob("rules/*.md")
        if path.name != "README.md"
    }


def codex_rule_sources(root):
    sources = set()
    for path in root.glob("rules/**/AGENTS.md"):
        for line in path.read_text().splitlines():
            if line.startswith("- `claude/rules/") and line.endswith("`"):
                sources.add(line.removeprefix("- `").removesuffix("`"))
    return sources


def report(label, source, target, errors):
    missing = source - target
    extra = target - source
    print(f"{label}: source={len(source)} target={len(target)}")
    if missing:
        errors.append(f"{label} missing: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{label} extra: {', '.join(sorted(extra))}")


def main():
    claude_root = Path(sys.argv[1] if len(sys.argv) > 1 else "claude")
    codex_root = Path(sys.argv[2] if len(sys.argv) > 2 else "codex")
    errors = []

    report("agents", claude_agent_names(claude_root), codex_agent_names(codex_root), errors)
    report("skills", claude_skill_names(claude_root), codex_skill_names(codex_root), errors)
    report("rules", claude_rule_paths(claude_root), codex_rule_sources(codex_root), errors)

    if errors:
        print("Transposition audit failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Transposition audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

