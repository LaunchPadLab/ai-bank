#!/usr/bin/env python3
"""Validate Codex AGENTS.md rule templates."""

import sys
from pathlib import Path


FORBIDDEN_SNIPPETS = ("---\n", "paths:", "alwaysApply:")


def validate_agents_md(path):
    errors = []
    text = path.read_text()
    if not text.startswith("# "):
        errors.append(f"{path}: must start with a Markdown heading, not frontmatter")
    if text.startswith("---"):
        errors.append(f"{path}: must not contain YAML frontmatter")
    if any(line.strip() == "---" for line in text.splitlines()):
        errors.append(f"{path}: contains an unstripped frontmatter delimiter")
    for snippet in FORBIDDEN_SNIPPETS[1:]:
        if snippet in text:
            errors.append(f"{path}: contains Claude/Cursor rule field '{snippet}'")
    if "Codex applies AGENTS.md instructions" not in text:
        errors.append(f"{path}: missing Codex scope explanation")
    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "codex/rules")
    if not root.exists():
        print(f"Codex rules directory not found: {root}")
        return 1

    paths = sorted(root.rglob("AGENTS.md"))
    errors = []
    for path in paths:
        errors.extend(validate_agents_md(path))

    if errors:
        print("Codex rules validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(paths)} Codex AGENTS.md templates successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
