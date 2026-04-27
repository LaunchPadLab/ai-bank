# Codex Instructions: app/policies

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/policies.md`

## Source: `claude/rules/policies.md`

# Pundit Policy Conventions

- One policy per resource: `app/policies/entity_policy.rb`
- Keep policies plain and explicit. Prefer boring instance methods over DSLs, concerns, `define_method`, or `method_missing`.
- Keep authorization local to the class. If Avo needs `view_*?`, `show_*?`, `edit_*?`, `destroy_*?`, or `create_*?`, define them directly in that policy.
- Default deny: return `false` unless explicitly allowed.
- Define a `Scope` class for `policy_scope` queries.
- Use `policy_scope(Model)` instead of `Model.all` in index actions.
- Controllers must call `authorize @resource` on every action.
- Test each policy’s real permission surface, including any Avo-specific association methods.
- Inheritance: `class EntityPolicy < ApplicationPolicy`
