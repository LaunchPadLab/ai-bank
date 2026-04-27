#!/usr/bin/env python3
"""Validate Codex skill package shape and frontmatter."""

import re
import sys
from pathlib import Path

from codex_transpose import CLAUDE_ONLY_SKILL_KEYS, hyphen_case, parse_frontmatter, strip_generated_artifacts


ALLOWED_FRONTMATTER = {"name", "description"}


def skill_dirs(root):
    return sorted(path.parent for path in root.glob("*/SKILL.md"))


def validate_skill(skill_dir):
    errors = []
    skill_md = skill_dir / "SKILL.md"
    metadata, _body = parse_frontmatter(skill_md.read_text())
    if not metadata:
        return [f"{skill_dir}: missing SKILL.md frontmatter"]

    missing = ALLOWED_FRONTMATTER - set(metadata)
    if missing:
        errors.append(f"{skill_dir}: missing field(s): {', '.join(sorted(missing))}")

    unexpected = set(metadata) - ALLOWED_FRONTMATTER
    if unexpected:
        errors.append(f"{skill_dir}: unexpected frontmatter field(s): {', '.join(sorted(unexpected))}")

    claude_only = set(metadata) & CLAUDE_ONLY_SKILL_KEYS
    if claude_only:
        errors.append(f"{skill_dir}: Claude-only frontmatter field(s): {', '.join(sorted(claude_only))}")

    name = metadata.get("name")
    if name:
        if not hyphen_case(name):
            errors.append(f"{skill_dir}: skill name must be kebab-case")
        if name != skill_dir.name:
            errors.append(f"{skill_dir}: skill name '{name}' does not match directory '{skill_dir.name}'")

    description = metadata.get("description")
    if not description or len(str(description).strip()) < 10:
        errors.append(f"{skill_dir}: description is missing or too short")

    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "codex/skills")
    if not root.exists():
        print(f"Codex skills directory not found: {root}")
        return 1
    if (root / "SKILL.md").exists():
        print("Codex skills root must not contain SKILL.md")
        return 1

    errors = []
    for path in root.rglob("*"):
        if strip_generated_artifacts(path):
            errors.append(f"Generated artifact should not be tracked: {path}")

    dirs = skill_dirs(root)
    seen = set()
    for skill_dir in dirs:
        metadata, _body = parse_frontmatter((skill_dir / "SKILL.md").read_text())
        name = metadata.get("name")
        if name in seen:
            errors.append(f"{skill_dir}: duplicate skill name '{name}'")
        seen.add(name)
        errors.extend(validate_skill(skill_dir))

    if errors:
        print("Codex skill validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(dirs)} Codex skills successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

