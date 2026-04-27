#!/usr/bin/env python3
"""
Validate all skill packages in a skills directory.

Usage:
    python scripts/validate_all_skills.py claude/skills
"""

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from quick_validate import parse_frontmatter, validate_skill


GENERATED_PATTERNS = ("__pycache__", ".pyc", ".pyo")
SKILL_REF_PATTERN = re.compile(
    r"(?:see:|see|use)\s+\**([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\**\s+skill",
    re.IGNORECASE,
)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def strip_fenced_code(content):
    return re.sub(r"```.*?```", "", content, flags=re.DOTALL)


def load_frontmatter(skill_md):
    content = skill_md.read_text()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    parsed = parse_frontmatter(match.group(1))
    return parsed if isinstance(parsed, dict) else {}


def find_skill_dirs(root):
    return sorted(path.parent for path in root.glob("*/SKILL.md"))


def check_root_skill(root, errors):
    if (root / "SKILL.md").exists():
        errors.append("Root claude/skills/SKILL.md should not be a skill package")


def check_generated_files(root, errors):
    for path in root.rglob("*"):
        path_text = str(path)
        if any(pattern in path_text for pattern in GENERATED_PATTERNS):
            errors.append(f"Generated artifact should not be tracked: {path.relative_to(root)}")


def check_unique_names(skill_dirs, errors):
    seen = {}
    for skill_dir in skill_dirs:
        metadata = load_frontmatter(skill_dir / "SKILL.md")
        name = metadata.get("name")
        if not name:
            continue
        if name in seen:
            errors.append(
                f"Duplicate skill name '{name}' in {skill_dir / 'SKILL.md'} "
                f"and {seen[name] / 'SKILL.md'}"
            )
        seen[name] = skill_dir
    return set(seen)


def check_markdown_links(root, errors):
    for markdown_file in root.rglob("*.md"):
        content = strip_fenced_code(markdown_file.read_text())
        for target in MARKDOWN_LINK_PATTERN.findall(content):
            if "://" in target or target.startswith("#") or target.startswith("mailto:"):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (markdown_file.parent / target_path).resolve()
            if not resolved.exists():
                errors.append(
                    f"Broken markdown link in {markdown_file.relative_to(root)}: {target}"
                )


def check_skill_references(root, skill_names, errors):
    for markdown_file in root.rglob("*.md"):
        content = strip_fenced_code(markdown_file.read_text())
        for candidate in SKILL_REF_PATTERN.findall(content):
            if candidate not in skill_names:
                errors.append(
                    f"Possible missing skill reference '{candidate}' in "
                    f"{markdown_file.relative_to(root)}"
                )


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "claude/skills").resolve()
    if not root.exists():
        print(f"Skills directory not found: {root}")
        return 1

    errors = []
    check_root_skill(root, errors)
    check_generated_files(root, errors)

    skill_dirs = find_skill_dirs(root)
    for skill_dir in skill_dirs:
        valid, message = validate_skill(skill_dir)
        if not valid:
            errors.append(f"{skill_dir.relative_to(root)}: {message}")

    skill_names = check_unique_names(skill_dirs, errors)
    check_markdown_links(root, errors)
    check_skill_references(root, skill_names, errors)

    if errors:
        print("Skill validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(skill_dirs)} skills successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
