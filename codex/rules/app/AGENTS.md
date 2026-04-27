# Codex Instructions: app

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/anti-patterns.md`

## Source: `claude/rules/anti-patterns.md`

# Anti-Patterns to Avoid

- **God object:** A class with unrelated reasons to change. Extract by responsibility: query objects for reads, concerns for shared horizontal behavior, services for orchestration, and presenters/components for display.
- **Service graveyard:** Do not create services for trivial CRUD or model-local behavior. `user.update!(name: params[:name])` is fine inline when it is the whole operation.
- **Anemic model:** Do not strip cohesive domain behavior from the model that owns the state just to keep models artificially thin.
- **Callback spaghetti:** Do not chain `after_create` or `after_save` callbacks for emails, jobs, APIs, or creating related records. Use explicit call sites or services for contextual side effects.
- **STI abuse:** Avoid STI when many columns are subtype-specific. Prefer separate tables or polymorphic associations when shapes diverge.
- **N+1 ignorance:** Eager-load associations you know will be accessed. Use `strict_loading` to catch accidental lazy loads in development.
- **Kitchen sink concern:** Concerns must be narrow and focused. If a concern has multiple responsibilities, split it or move orchestration elsewhere.
