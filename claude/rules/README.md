# Claude Rules

Rules provide persistent guidance for Claude when working in this repository.

## Frontmatter

Use YAML frontmatter on every rule file.

File-specific rules use `paths`:

```yaml
---
paths:
  - "app/models/**/*.rb"
  - "test/models/**/*.rb"
---
```

Always-available rules omit `paths`. Claude Code loads rules without `paths` at launch with the same priority as `.claude/CLAUDE.md`:

```yaml
---
---
```

Do not use Cursor's `alwaysApply` field in Claude rules. That field belongs to Cursor `RULE.md` / `.mdc` rules.

## Scope

- Keep rules concise and convention-focused.
- Put detailed workflows in `claude/skills`.
- Use agents for role-specific behavior and orchestration.
- Keep Cursor-specific rules in `cursor/rules/**/RULE.md`; those use `description`, `globs`, and `alwaysApply`.

## Validation

Run after editing rules:

```bash
python3 claude/rules/scripts/validate_rules.py claude/rules
```

Docs validation note: Context7 and Firecrawl MCP calls were blocked by a wrapper that did not pass required arguments. A web fallback against Claude Code memory documentation confirmed that `.claude/rules/` files without `paths` load unconditionally, and files with `paths` load when matching files are read.
