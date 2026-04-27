# Codex Instructions: test/services

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/services.md`

## Source: `claude/rules/services.md`

# Service Object Conventions

- Use services for real orchestration: cross-model workflows, transactions, side effects, external APIs, or logic reused across multiple entry points.
- Do not extract single-record aggregate behavior into a service; put it on the model that owns the state.
- Do not create tiny wrapper services for mail delivery. Call mailers directly at the explicit call site unless delivery is part of broader orchestration.
- Prefer direct model or controller code when it is clearer than adding another object.
- Keep services plain: one public method (`#call`), explicit dependencies, and no framework-y DSL.
- Prefer plain return values and Rails exceptions/validations over custom result structs unless explicit status handling materially improves clarity.
- Use transactions or `with_lock` inside the model or service that owns the state transition.
- Test the real behavior at the boundary that matters: model for domain rules, controller for request flow, integration for end-to-end behavior.
