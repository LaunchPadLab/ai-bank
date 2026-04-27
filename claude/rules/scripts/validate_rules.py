#!/usr/bin/env python3
"""
Validate Claude rule files.

Usage:
    python3 claude/rules/scripts/validate_rules.py claude/rules
"""

import re
import sys
from pathlib import Path


BANNED_TERMS = [
    "have_enqueued_job",
    "have_enqueued_mail",
    "ios/CLAUDE.md",
    "LifeMuse",
    "Member app",
    "FactoryBot",
    "factory",
    "Solid Queue",
]


def parse_frontmatter(text):
    match = re.match(r"^---\n(.*?)---\n?", text, re.DOTALL)
    if not match:
        return None, text

    metadata = {}
    lines = match.group(1).splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith(" ") or ":" not in line:
            index += 1
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not value:
            values = []
            index += 1
            while index < len(lines) and lines[index].startswith(" "):
                item = lines[index].strip()
                if item.startswith("- "):
                    values.append(item[2:].strip().strip('"\''))
                index += 1
            metadata[key] = values
            continue

        if value.lower() == "true":
            metadata[key] = True
        elif value.lower() == "false":
            metadata[key] = False
        else:
            metadata[key] = value.strip('"\'')
        index += 1

    return metadata, text[match.end():]


def validate_rule(path):
    errors = []
    text = path.read_text()
    metadata, body = parse_frontmatter(text)

    if metadata is None:
        return [f"{path.name}: missing YAML frontmatter"]

    has_paths = "paths" in metadata
    if "alwaysApply" in metadata:
        errors.append(f"{path.name}: do not use Cursor alwaysApply in Claude rules; omit paths for global rules")

    if has_paths:
        paths = metadata["paths"]
        if not isinstance(paths, list) or not paths or not all(isinstance(item, str) for item in paths):
            errors.append(f"{path.name}: paths must be a non-empty list of strings")

    for term in BANNED_TERMS:
        if term in body:
            errors.append(f"{path.name}: stale or banned term found: {term}")

    if "account_id" in body and "foreign_key: true" in body:
        errors.append(f"{path.name}: account_id must not recommend foreign_key: true")

    if path.name == "cli.md":
        for command in ["kill -9", "db:reset", "rubocop -A", "bin/rails destroy"]:
            if command in body and "Ask First" not in body and "ask first" not in body:
                errors.append(f"{path.name}: unsafe command lacks ask-first guidance: {command}")

    return errors


def main():
    rules_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "claude/rules").resolve()
    errors = []

    for path in sorted(rules_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        errors.extend(validate_rule(path))

    if errors:
        print("Rule validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len([p for p in rules_dir.glob('*.md') if p.name != 'README.md'])} rules successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
