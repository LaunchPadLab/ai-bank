#!/usr/bin/env python3
"""Transpose Claude path rules into Codex AGENTS.md templates."""

import argparse
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from codex_transpose import read_markdown_with_frontmatter


def source_rule_paths(source):
    return sorted(path for path in source.glob("*.md") if path.name != "README.md")


def path_bucket(pattern):
    parts = [part for part in str(pattern).strip("'\"").split("/") if part]
    base = []
    for part in parts:
        if any(marker in part for marker in ("*", "?", "[")):
            break
        base.append(part)

    if not base:
        return "root"
    if "." in base[-1]:
        base = base[:-1]
    return "/".join(base) if base else "root"


def rule_buckets(metadata):
    paths = metadata.get("paths")
    if not paths:
        return {"root"}
    return {path_bucket(path) for path in paths}


def scope_title(bucket):
    if bucket == "root":
        return "Root Project Scope"
    return bucket


def write_agents_md(bucket, entries, output_root):
    directory = output_root / bucket
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "AGENTS.md"

    lines = [
        f"# Codex Instructions: {scope_title(bucket)}",
        "",
        "This AGENTS.md template was transposed from Claude rule files.",
        "Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.",
        "",
        "## Included Source Rules",
        "",
    ]

    for source_path, _body in entries:
        lines.append(f"- `{source_path}`")

    for source_path, body in entries:
        lines.extend([
            "",
            f"## Source: `{source_path}`",
            "",
            body.strip(),
            "",
        ])

    target.write_text("\n".join(lines).rstrip() + "\n")


def transpose(source, output):
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    grouped = defaultdict(list)
    for rule_path in source_rule_paths(source):
        metadata, body = read_markdown_with_frontmatter(rule_path)
        for bucket in sorted(rule_buckets(metadata)):
            grouped[bucket].append((rule_path.as_posix(), body))

    for bucket, entries in grouped.items():
        write_agents_md(bucket, entries, output)

    return len(grouped)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="claude/rules")
    parser.add_argument("--output", default="codex/rules")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"Claude rules directory not found: {source}", file=sys.stderr)
        return 1

    count = transpose(source, Path(args.output))
    print(f"Transposed Claude rules into {count} Codex AGENTS.md templates under {args.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

