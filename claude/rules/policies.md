---
paths:
  - "app/policies/**/*.rb"
  - "test/policies/**/*.rb"
---

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