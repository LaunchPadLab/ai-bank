#!/usr/bin/env python3
"""Shared helpers for transposing Claude assets into Codex assets."""

import json
import re
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n?---\n?", re.DOTALL)
HYphen_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CLAUDE_ONLY_SKILL_KEYS = {
    "allowed-tools",
    "argument-hint",
    "context",
    "agent",
    "disable-model-invocation",
    "user-invocable",
    "license",
    "metadata",
}
CLAUDE_ONLY_AGENT_KEYS = {
    "maxTurns",
    "permissionMode",
    "disallowedTools",
    "background",
    "memory",
    "color",
    "isolation",
}


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

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

        if value in {">", ">-", "|", "|-"}:
            index += 1
            block = []
            while index < len(lines) and (lines[index].startswith(" ") or not lines[index].strip()):
                block.append(lines[index].strip())
                index += 1
            metadata[key] = " ".join(part for part in block if part)
            continue

        if not value:
            index += 1
            values = []
            while index < len(lines) and lines[index].startswith(" "):
                item = lines[index].strip()
                if item.startswith("- "):
                    values.append(item[2:].strip().strip("'\""))
                index += 1
            metadata[key] = values
            continue

        if value.startswith("[") and value.endswith("]"):
            metadata[key] = [
                item.strip().strip("'\"")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        elif value.lower() == "true":
            metadata[key] = True
        elif value.lower() == "false":
            metadata[key] = False
        else:
            metadata[key] = value.strip("'\"")
        index += 1

    return metadata, text[match.end():]


def read_markdown_with_frontmatter(path):
    return parse_frontmatter(Path(path).read_text())


def codex_text(text):
    return (
        str(text)
        .replace("Claude Code", "Codex")
        .replace("Claude's", "Codex's")
        .replace("Claude", "Codex")
    )


def yaml_scalar(value):
    return json.dumps(str(value), ensure_ascii=True)


def toml_scalar(value):
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    if "'''" not in text:
        return "'''" + text + "'''"
    return json.dumps(text.replace("\\", "\\\\"), ensure_ascii=True)


def hyphen_case(value):
    return bool(HYphen_CASE_RE.match(str(value)))


def strip_generated_artifacts(path):
    text = str(path)
    return "__pycache__" in text or text.endswith((".pyc", ".pyo"))


def strip_frontmatter(text):
    return FRONTMATTER_RE.sub("", text, count=1)
