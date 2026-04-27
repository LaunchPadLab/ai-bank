#!/usr/bin/env python3
"""Transpose Claude skill packages into Codex skill packages."""

import argparse
import shutil
import sys
from pathlib import Path

from codex_transpose import (
    CLAUDE_ONLY_SKILL_KEYS,
    codex_text,
    read_markdown_with_frontmatter,
    strip_generated_artifacts,
    yaml_scalar,
)


def source_skill_dirs(source):
    return sorted(path.parent for path in source.glob("*/SKILL.md"))


def copy_skill(source_dir, output_dir):
    if output_dir.exists():
        shutil.rmtree(output_dir)

    def ignore(_directory, names):
        return [
            name for name in names
            if strip_generated_artifacts(Path(_directory) / name)
        ]

    shutil.copytree(source_dir, output_dir, ignore=ignore)
    normalize_skill_md(output_dir / "SKILL.md")


def normalize_skill_md(skill_md):
    metadata, body = read_markdown_with_frontmatter(skill_md)
    name = metadata.get("name", skill_md.parent.name)
    description = codex_text(metadata.get("description", ""))
    omitted = sorted(set(metadata) & CLAUDE_ONLY_SKILL_KEYS)

    notes = ""
    if omitted:
        notes = (
            "<!-- Codex transposition: omitted Claude-specific frontmatter fields: "
            + ", ".join(omitted)
            + ". -->\n\n"
        )

    skill_md.write_text(
        "---\n"
        f"name: {yaml_scalar(name)}\n"
        f"description: {yaml_scalar(description)}\n"
        "---\n\n"
        + notes
        + codex_text(body.lstrip())
    )


def transpose(source, output):
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    count = 0
    for skill_dir in source_skill_dirs(source):
        copy_skill(skill_dir, output / skill_dir.name)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="claude/skills")
    parser.add_argument("--output", default="codex/skills")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"Claude skills directory not found: {source}", file=sys.stderr)
        return 1

    count = transpose(source, Path(args.output))
    print(f"Transposed {count} Claude skills into {args.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

