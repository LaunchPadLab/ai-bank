# Codex Instructions: test/models

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/models.md`

## Source: `claude/rules/models.md`

# Model Conventions

- Put cohesive domain behavior on the model that owns the state.
- Keep models focused: validations, associations, scopes, state transitions, predicates, and aggregate-local behavior.
- Use concerns for shared horizontal behavior across models.
- Use query objects for reusable read/query complexity.
- Use form objects for complex input or persistence boundaries.
- Use services for orchestration across models, transactions, side effects, or external systems.
- Use callbacks only for local data normalization and defaults.
- Do not trigger emails, API calls, or broad job orchestration from model callbacks.
- Always specify `dependent:` on `has_many` and `has_one` associations.
- Use enum hash syntax with explicit values, and avoid reserved column names such as `type`.
- Validate required data in the model and with database constraints where appropriate.
- Use scopes for simple reusable queries; use query objects for complex queries.
- Provide fixtures for meaningful model states in `test/fixtures/`.
