# Codex Instructions: app/components

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/styles.md`
- `claude/rules/views.md`

## Source: `claude/rules/styles.md`

# Style Principles

## Responsive Design

- Use mobile-first responsive design.
- Start with base mobile styles and layer up with `sm:`, `md:`, and `lg:`.
- Avoid desktop-first overrides.

## Interaction and Accessibility

- Every clickable or focusable element needs visible hover/focus states.
- Use `focus:ring-*` or equivalent focus styling for keyboard users.
- Icon-only buttons need `aria-label`.
- Navigation links need `aria-current` for the active page.
- Form inputs need associated `<label>` elements.
- Use `role="alert"` for flash or error messages that should be announced.

## Tailwind Conventions

- Use Tailwind utilities instead of inline `style=""` attributes.
- Avoid arbitrary values such as `w-[372px]` or `mt-[13px]` unless there is a clear design reason.
- Follow the semantic color palette: blue for primary actions, green for success, red for destructive/errors, yellow for warnings, and gray for neutral/secondary UI.
- Extract repeated class combinations into ViewComponents when reuse is meaningful.
- Add custom `@utility` rules only for broadly reused patterns that cannot reasonably live in a component.


## Source: `claude/rules/views.md`

# View & Component Conventions

- Use ViewComponents (`app/components/`) for reusable UI elements over partials
- Use presenters (`app/presenters/`) with SimpleDelegator for formatting logic
- No business logic in views -- use presenters for display formatting
- Turbo Frames for partial page updates; Turbo Streams for multi-target updates
- Stimulus controllers for client-side behavior (minimal JS, progressive enhancement)
- Tailwind CSS 4 utility classes for styling
- Always include ARIA attributes for accessibility (WCAG 2.1 AA)
