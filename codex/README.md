# Codex Catalog

This directory contains Codex-native versions of the Claude assets in this repository.

## Runtime Targets

- Copy `codex/agents/*.toml` into a project-scoped `.codex/agents/` directory, or into `~/.codex/agents/` for personal agents.
- Copy `codex/skills/*` into the desired Codex skill root.
- Copy selected `codex/rules/**/AGENTS.md` templates into matching project directories.

Codex custom subagents are standalone TOML files with `name`, `description`, and `developer_instructions`. Codex skills are `SKILL.md` packages. Codex persistent rules are `AGENTS.md` files scoped by their directory tree, not Claude-style `paths:` globs.

## Regenerating

Run from the repository root:

```bash
python3 codex/scripts/transpose_claude_skills.py
python3 codex/scripts/transpose_claude_agents.py
python3 codex/scripts/transpose_claude_rules.py
```

The agent transposition expects `codex/skills` to exist first so it can enable matching skills through `skills.config`.

## Validation

```bash
python3 codex/scripts/validate_codex_skills.py codex/skills
python3 codex/scripts/validate_codex_agents.py codex/agents
python3 codex/scripts/validate_codex_rules.py codex/rules
python3 codex/scripts/audit_transposition.py claude codex
```

