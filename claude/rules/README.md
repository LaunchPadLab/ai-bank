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

Always-available rules use `alwaysApply: true`:

```yaml
---
alwaysApply: true
---
```

The local validator accepts either `paths` or `alwaysApply: true`. If the active Claude runner supports a different always-available convention, update this README and the validator together.

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

Context7 note: this cleanup attempted to validate Claude rule documentation with Context7, but the available MCP wrapper did not pass the required `query` and `libraryName` arguments. Until that is fixed, this directory follows the local `README.md` convention.
