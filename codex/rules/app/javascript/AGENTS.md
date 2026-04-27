# Codex Instructions: app/javascript

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/frontend.md`

## Source: `claude/rules/frontend.md`

# Frontend Conventions

- Prefer Hotwire (Turbo + Stimulus) over SPA frameworks.
- Keep JavaScript thin and focused on progressive enhancement.
- Put Stimulus controllers in `app/javascript/controllers/`.
- Use Turbo Frames and Turbo Streams for server-rendered UI updates.
- Ask before adding npm packages or introducing a new frontend build stack.
- For native shell decisions, defer to the Hotwire Native iOS/Android skills and app-specific files.
