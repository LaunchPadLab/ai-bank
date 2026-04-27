---
paths:
  - "app/assets/stylesheets/**/*.css"
  - "app/assets/stylesheets/**/*.scss"
  - "app/views/**/*.erb"
  - "app/components/**/*.erb"
---

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
