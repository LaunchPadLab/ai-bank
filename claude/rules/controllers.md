---
paths:
  - "app/controllers/**/*.rb"
  - "test/controllers/**/*.rb"
---

# Controller Conventions

- Prefer standard REST actions: `index`, `show`, `new`, `create`, `edit`, `update`, `destroy`.
- Keep controllers focused on HTTP orchestration: load records, authorize, call domain behavior, and render/redirect.
- Simple CRUD can stay directly in the controller.
- Delegate when orchestration, transactions, side effects, external systems, or cross-model workflows justify it.
- Use Rails 8 strong parameters with `params.expect(resource: [ ... ])` for new code. Preserve existing `params.require(...).permit(...)` unless you are already touching that controller.
- Use presenters or ViewComponents for display formatting, not controllers.
- Use `respond_to` with `format.html` and `format.turbo_stream` for Hotwire flows.
- Always test authentication, authorization, valid params, invalid params, and cross-account isolation where relevant.
