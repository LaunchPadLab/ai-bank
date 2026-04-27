# Codex Instructions: app/presenters

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/views.md`

## Source: `claude/rules/views.md`

# View & Component Conventions

- Use ViewComponents (`app/components/`) for reusable UI elements over partials
- Use presenters (`app/presenters/`) with SimpleDelegator for formatting logic
- No business logic in views -- use presenters for display formatting
- Turbo Frames for partial page updates; Turbo Streams for multi-target updates
- Stimulus controllers for client-side behavior (minimal JS, progressive enhancement)
- Tailwind CSS 4 utility classes for styling
- Always include ARIA attributes for accessibility (WCAG 2.1 AA)
