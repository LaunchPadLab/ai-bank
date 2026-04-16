---
paths:
  - "app/controllers/avo/**/*.rb"
  - "test/controllers/avo/**/*.rb"
---

# Controller Conventions

- Always `authorize` with Pundit on every action
- Use `policy_scope(Model)` for index queries (multi-tenant isolation)