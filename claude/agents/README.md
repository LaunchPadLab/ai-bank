# Agents Contributor Guide

This directory contains Markdown agent definitions. Agent prompts should stay aligned with the canonical skills under `claude/skills`.

## Frontmatter

Required fields:

- `name`: kebab-case and matching the file basename.
- `description`: what the agent does and when to use it.
- `model`: usually `inherit`. `prompt-engineer` intentionally uses `sonnet`.

Optional fields:

- `skills`: preload canonical skill packages by slug.
- `maxTurns`: cap focused workflows with predictable scope.
- `disallowedTools` and `permissionMode`: enforce read-only or plan-only agents.
- `isolation`: use for orchestrators that need isolated worktrees.
- `background` and `memory`: use for longer-running reviewers or auditors that need project context.
- `color`: include only if the active runner supports it.

## Skill Ownership

- `rails-expert` owns broad architectural guidance and preloads `rails-architecture`.
- `frontend-developer` owns Rails UI work and preloads Turbo, Stimulus, Tailwind, and ViewComponent skills.
- `hotwire-native-ios-agent` and `hotwire-native-android-agent` own platform-specific Hotwire Native work and preload auth/path-config support.
- `test-agent`, `tdd-red-agent`, and `tdd-refactoring-agent` own testing and TDD phase workflows.
- `performance-monitor`, `database-optimizer`, `postgres-pro`, `caching-agent`, and `review-agent` share performance ownership by layer.
- Skills without dedicated agents should be invoked by the closest owning agent rather than duplicated in prompt bodies.

## Prompt Guidelines

- Start with local repository discovery, not a nonexistent context service.
- Reference only agents that exist in this directory or generic human roles.
- If a skill and an agent disagree, fix the drift and keep the skill as the detailed source of truth.
- Keep read-only agents free of default implementation language.

## Validation

Run the agent validator after adding or changing agents:

```bash
python3 claude/agents/scripts/validate_agents.py claude/agents claude/skills
```
