---
paths:
  - "**/*.js"
  - "**/*.ts"
  - "app/javascript/**/*"
  - "package.json"
---

# Frontend Conventions

- Prefer Hotwire (Turbo + Stimulus) over SPA frameworks.
- Keep JavaScript thin and focused on progressive enhancement.
- Put Stimulus controllers in `app/javascript/controllers/`.
- Use Turbo Frames and Turbo Streams for server-rendered UI updates.
- Ask before adding npm packages or introducing a new frontend build stack.
- For native shell decisions, defer to the Hotwire Native iOS/Android skills and app-specific files.
