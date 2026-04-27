#!/usr/bin/env python3
"""
Validate agent definitions.

Usage:
    python3 claude/agents/scripts/validate_agents.py claude/agents claude/skills
"""

import re
import sys
from pathlib import Path


REQUIRED_FIELDS = {"name", "description", "model"}
STALE_TERMS = [
    "context-manager",
    "runSubagent",
    "Rails 7",
    "React 18",
    "Vue 3",
    "Angular 15",
]
PHANTOM_COLLABORATORS = {
    "qa-expert",
    "performance-engineer",
    "websocket-engineer",
    "deployment-engineer",
    "security-auditor",
    "devops-engineer",
    "fullstack-developer",
    "api-designer",
    "legal-advisor",
    "data-engineer",
    "cloud-architect",
    "risk-manager",
    "privacy-officer",
    "llm-architect",
    "ai-engineer",
    "data-scientist",
    "backend-developer",
    "ml-engineer",
    "nlp-engineer",
    "product-manager",
    "ux-researcher",
    "accessibility-tester",
    "content-marketer",
    "agent-organizer",
    "error-coordinator",
    "workflow-orchestrator",
    "task-distributor",
    "knowledge-synthesizer",
    "multi-agent-coordinator",
}
READ_ONLY_BAD_PHRASES = [
    "implement solutions",
    "deploy compliance controls",
    "implemented automated",
    "certification achieved",
]


def parse_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
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

        if value in {">", ">-"}:
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
                    values.append(item[2:].strip())
                index += 1
            metadata[key] = values
            continue

        if value.startswith("[") and value.endswith("]"):
            metadata[key] = [
                item.strip().strip("'\"")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            metadata[key] = value.strip("'\"")
        index += 1

    body = text[match.end():]
    return metadata, body


def available_skills(skills_dir):
    return {path.parent.name for path in skills_dir.glob("*/SKILL.md")}


def available_agents(agents_dir):
    return {path.stem for path in agents_dir.glob("*.md") if path.name != "README.md"}


def is_read_only(metadata):
    disallowed = str(metadata.get("disallowedTools", ""))
    return "Write" in disallowed and "Edit" in disallowed


def validate_agent(path, skills, agents):
    errors = []
    text = path.read_text()
    metadata, body = parse_frontmatter(text)
    if metadata is None:
        return [f"{path.name}: missing YAML frontmatter"]

    missing = REQUIRED_FIELDS - set(metadata)
    if missing:
        errors.append(f"{path.name}: missing required field(s): {', '.join(sorted(missing))}")

    name = metadata.get("name")
    if name and name != path.stem:
        errors.append(f"{path.name}: name '{name}' does not match filename '{path.stem}'")

    declared_skills = metadata.get("skills", [])
    if isinstance(declared_skills, str):
        declared_skills = [declared_skills]
    for skill in declared_skills:
        if skill not in skills:
            errors.append(f"{path.name}: unknown skill '{skill}'")

    for term in STALE_TERMS:
        if term in text:
            errors.append(f"{path.name}: stale term found: {term}")

    for collaborator in PHANTOM_COLLABORATORS:
        if collaborator in text and collaborator not in agents:
            errors.append(f"{path.name}: phantom collaborator found: {collaborator}")

    if is_read_only(metadata):
        lowered = body.lower()
        for phrase in READ_ONLY_BAD_PHRASES:
            if phrase in lowered:
                errors.append(f"{path.name}: read-only agent contains implementation phrase: {phrase}")

    return errors


def main():
    agents_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "claude/agents").resolve()
    skills_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "claude/skills").resolve()

    skills = available_skills(skills_dir)
    agents = available_agents(agents_dir)
    errors = []

    for path in sorted(agents_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        errors.extend(validate_agent(path, skills, agents))

    if errors:
        print("Agent validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(agents)} agents successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
