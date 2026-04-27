# Skills Contributor Guide

This directory contains skill packages. Each skill lives in a named folder with a `SKILL.md` file and optional supporting resources.

## Package Structure

- Use one canonical `SKILL.md` per skill folder.
- Do not place a root-level `claude/skills/SKILL.md`; the root directory is a container, not a skill.
- Use `reference/` or `references/` for supporting Markdown that should be loaded only when needed. Existing packages use both spellings; keep local links stable and document new packages with the spelling already used by neighboring skills.
- Use `scripts/` for deterministic helpers and exclude generated files such as `__pycache__/` and `*.pyc`.
- Use `templates/` for source templates that agents copy or adapt.

## Frontmatter Profiles

### Generator or Action Skill

Use for skills that create or edit code.

```yaml
---
name: rails-model-generator
description: Creates Rails models using TDD...
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---
```

### Reference Skill

Use for pattern catalogs that should attach only when another workflow needs them.

```yaml
---
name: turbo-patterns
description: Reference material for Turbo Frames, Turbo Streams, morphing, and Hotwire UI updates...
user-invocable: false
---
```

Keep the description specific and avoid imperative wording such as "Creates" or "Implements" when `user-invocable: false` is set.

### Forked Analysis Skill

Use for review, planning, and specification workflows that should run in a separate context and avoid code edits.

```yaml
---
name: code-review
description: Reviews existing Rails code for defects...
disable-model-invocation: true
argument-hint: "[file-or-directory]"
context: fork
agent: Explore
---
```

### Runtime-Specific Fields

Fields such as `context`, `agent`, `argument-hint`, `user-invocable`, and `disable-model-invocation` are runner-specific. When adding or changing them, keep `skill-creator/scripts/quick_validate.py` in sync.

## Trigger Boundaries

- Prefer concrete trigger words over broad nouns.
- Keep overlapping domains distinct:
  - Action Cable: channels, subscriptions, WebSocket connections.
  - Turbo: Frames, Streams, morphing, server-rendered UI updates.
  - Caching: fragment caching, cache keys, Russian doll caching.
  - Performance: N+1 queries, query plans, memory, profiling, Bullet.
  - Authentication: sign in/out and sessions.
  - Authorization: Pundit policies and permission rules.

## Verification Sections

Skills that can lead to code edits should end with a short `Agent Verification` section covering the smallest useful test command, lint check, and browser/manual smoke check when relevant.
