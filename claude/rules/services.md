---
paths:
  - "app/services/**/*.rb"
  - "test/services/**/*.rb"
---

# Service Object Conventions

- Use a service only for real orchestration: multi-model work, external APIs, or logic reused across multiple entry points.
- Do not extract single-record domain behavior into a service. Put it on the model that owns the state.
- Do not create tiny wrapper services for mail delivery. Call mailers directly at the explicit call site.
- Prefer direct model or controller code when it is clearer than adding another object.
- If a service exists, keep it plain: one public method (`#call`), no `ApplicationService` base class, and no framework-y DSL.
- Prefer plain return values over custom `Result` structs unless multiple values or explicit status handling materially improve clarity.
- Use transactions or `with_lock` inside the model or service that owns the state transition.
- Test the real behavior at the boundary that matters: model for domain rules, controller for request flow, integration for end-to-end behavior.
