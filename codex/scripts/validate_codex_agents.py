#!/usr/bin/env python3
"""Validate Codex custom subagent TOML files."""

import re
import sys
import tomllib
from pathlib import Path

from codex_transpose import CLAUDE_ONLY_AGENT_KEYS, hyphen_case


REQUIRED_FIELDS = {"name", "description", "developer_instructions"}
ALLOWED_TOP_LEVEL = {
    "name",
    "description",
    "developer_instructions",
    "nickname_candidates",
    "model",
    "model_reasoning_effort",
    "sandbox_mode",
    "mcp_servers",
    "skills",
}


def validate_agent(path):
    errors = []
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        return [f"{path}: invalid TOML: {error}"]

    missing = REQUIRED_FIELDS - set(data)
    if missing:
        errors.append(f"{path}: missing required field(s): {', '.join(sorted(missing))}")

    unexpected = set(data) - ALLOWED_TOP_LEVEL
    if unexpected:
        errors.append(f"{path}: unexpected top-level field(s): {', '.join(sorted(unexpected))}")

    claude_only = set(data) & CLAUDE_ONLY_AGENT_KEYS
    if claude_only:
        errors.append(f"{path}: Claude-only field(s): {', '.join(sorted(claude_only))}")

    name = data.get("name")
    if name:
        if not hyphen_case(name):
            errors.append(f"{path}: name must be kebab-case")
        if name != path.stem:
            errors.append(f"{path}: name '{name}' does not match filename '{path.stem}'")

    if data.get("sandbox_mode") and data["sandbox_mode"] not in {"read-only", "workspace-write", "danger-full-access"}:
        errors.append(f"{path}: unsupported sandbox_mode '{data['sandbox_mode']}'")

    if "skills" in data:
        configs = data["skills"].get("config", [])
        if not isinstance(configs, list):
            errors.append(f"{path}: skills.config must be an array of tables")
        for index, config in enumerate(configs):
            skill_path = config.get("path")
            if not skill_path:
                errors.append(f"{path}: skills.config[{index}] missing path")
                continue
            resolved = (path.parent / skill_path).resolve()
            if not resolved.exists():
                errors.append(f"{path}: skills.config[{index}] path does not exist: {skill_path}")

    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "codex/agents")
    if not root.exists():
        print(f"Codex agents directory not found: {root}")
        return 1

    errors = []
    agent_paths = sorted(root.glob("*.toml"))
    for path in agent_paths:
        errors.extend(validate_agent(path))

    if errors:
        print("Codex agent validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(agent_paths)} Codex agents successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

