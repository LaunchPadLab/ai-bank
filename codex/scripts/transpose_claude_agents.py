#!/usr/bin/env python3
"""Transpose Claude subagent Markdown files into Codex custom subagent TOML files."""

import argparse
import re
import shutil
import sys
from pathlib import Path

from codex_transpose import read_markdown_with_frontmatter, toml_scalar


READ_ONLY_NAME_MARKERS = (
    "review",
    "auditor",
    "audit",
    "security",
    "plan",
    "explorer",
    "docs-researcher",
    "docs_researcher",
)
CODEX_MODEL_PREFIXES = ("gpt-", "codex-", "o")


def source_agent_paths(source):
    return sorted(path for path in source.glob("*.md") if path.name != "README.md")


def normalize_agent_references(text):
    return re.sub(r"@([a-z][a-z0-9-]+)", r"\1", text)


def codex_model_value(value):
    model = str(value or "").strip()
    if not model or model == "inherit":
        return None
    if model.startswith(CODEX_MODEL_PREFIXES):
        return model
    return None


def read_only(metadata):
    name = str(metadata.get("name", "")).lower()
    description = str(metadata.get("description", "")).lower()
    disallowed = str(metadata.get("disallowedTools", ""))
    permission_mode = str(metadata.get("permissionMode", "")).lower()

    if "Write" in disallowed and "Edit" in disallowed:
        return True
    if permission_mode in {"plan", "read-only", "readonly"}:
        return True
    return any(marker in name or marker in description for marker in READ_ONLY_NAME_MARKERS)


def skill_config_lines(skills, codex_skills):
    lines = []
    for skill in skills:
        if (codex_skills / skill / "SKILL.md").exists():
            lines.extend([
                "",
                "[[skills.config]]",
                f"path = {toml_scalar(f'../skills/{skill}/SKILL.md')}",
                "enabled = true",
            ])
    return lines


def transposed_body(source_path, body, skills):
    intro = [
        f"Ported from `{source_path}` for Codex custom subagents.",
        "Use Codex subagent behavior: stay within the assigned role, return concise results to the parent agent, and do not assume unrelated context.",
    ]
    if skills:
        intro.append(
            "Related Codex skills are enabled through this TOML file when the matching skill package exists."
        )
    return "\n".join(intro) + "\n\n" + normalize_agent_references(body.strip()) + "\n"


def write_agent(source_path, output_path, codex_skills):
    metadata, body = read_markdown_with_frontmatter(source_path)
    name = metadata.get("name", source_path.stem)
    description = metadata.get("description", "")
    skills = metadata.get("skills", [])
    if isinstance(skills, str):
        skills = [skills]

    lines = [
        f"name = {toml_scalar(name)}",
        f"description = {toml_scalar(description)}",
    ]

    model = codex_model_value(metadata.get("model"))
    if model:
        lines.append(f"model = {toml_scalar(model)}")
    elif metadata.get("model") not in {None, "inherit"}:
        lines.append(f"# Source Claude model override omitted because it is not a Codex model: {metadata.get('model')}")

    if read_only(metadata):
        lines.append('sandbox_mode = "read-only"')

    lines.append(f"developer_instructions = {toml_scalar(transposed_body(source_path, body, skills))}")
    lines.extend(skill_config_lines(skills, codex_skills))
    output_path.write_text("\n".join(lines) + "\n")


def transpose(source, output, codex_skills):
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    count = 0
    for source_path in source_agent_paths(source):
        metadata, _body = read_markdown_with_frontmatter(source_path)
        name = metadata.get("name", source_path.stem)
        write_agent(source_path, output / f"{name}.toml", codex_skills)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="claude/agents")
    parser.add_argument("--output", default="codex/agents")
    parser.add_argument("--codex-skills", default="codex/skills")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"Claude agents directory not found: {source}", file=sys.stderr)
        return 1

    count = transpose(source, Path(args.output), Path(args.codex_skills))
    print(f"Transposed {count} Claude agents into {args.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

