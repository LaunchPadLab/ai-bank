---
paths:
  - "app/jobs/**/*.rb"
  - "test/jobs/**/*.rb"
---

# Background Job Conventions

- Use native Sidekiq jobs by default: `include Sidekiq::Job`.
- Enqueue native jobs with `perform_async`, `perform_in`, or `perform_at`.
- Configure retries with `sidekiq_options retry:`.
- Jobs must be idempotent and safe to retry.
- Pass IDs, not full objects, to avoid serialization and stale object issues.
- Handle missing records explicitly inside `perform`.
- Keep jobs focused: one job, one responsibility.
- Test native jobs with `Sidekiq::Testing.fake!`, class `.jobs.size`, `.drain`, or inline mode.
- Do not mix Active Job assertions with native Sidekiq jobs.
