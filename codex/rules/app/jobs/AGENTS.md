# Codex Instructions: app/jobs

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/jobs.md`

## Source: `claude/rules/jobs.md`

# Background Job Conventions

- Use the application's configured Rails queue backend. Use native Sidekiq APIs only when the repo has already chosen native Sidekiq.
- For Active Job, enqueue with `perform_later`/`set(wait:)`. For native Sidekiq, enqueue with `perform_async`, `perform_in`, or `perform_at`.
- Configure retries using the backend's native mechanism.
- Jobs must be idempotent and safe to retry.
- Pass IDs, not full objects, to avoid serialization and stale object issues.
- Handle missing records explicitly inside `perform`.
- Keep jobs focused: one job, one responsibility.
- Test through Active Job assertions for Active Job classes and backend-specific helpers for native workers.
- Do not mix Active Job assertions with native backend workers.
