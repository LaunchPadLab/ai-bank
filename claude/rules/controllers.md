---
paths:
  - "app/controllers/**/*.rb"
  - "test/controllers/**/*.rb"
---

# Controller Conventions

- Keep controllers thin: orchestrate, don't implement business logic
- Delegate to service objects for anything beyond simple CRUD
- Use strong parameters (`params.require(:x).permit(...)`)
- Use presenters (`app/presenters/`) for view formatting, not controllers
- Follow REST conventions: index, show, new, create, edit, update, destroy
- Prefer `respond_to` with `format.html` and `format.turbo_stream` for Hotwire
- Always test: authentication, authorization (404 for unauthorized), valid/invalid params