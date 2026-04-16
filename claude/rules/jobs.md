---
paths:
  - "app/jobs/**/*.rb"
  - "test/jobs/**/*.rb"
---

# Background Job Conventions

- Use Sidekiq
- Jobs must be idempotent -- safe to retry
- Pass IDs, not full objects (serialization safety)
- Use `discard_on ActiveRecord::RecordNotFound` for deleted records
- Use `retry_on` with specific exceptions and limits
- Keep jobs focused: one job, one responsibility
- Test with `have_enqueued_job` matcher