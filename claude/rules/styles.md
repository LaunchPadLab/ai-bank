---
paths:
  - "app/assets/stylesheets/**/*.rb"
  - "app/views/**/*.erb"
---

# Style Principles

## Member App Styles

- Mobile-first responsive design Always start with base (mobile) styles and layer up with `sm:`, `md:`, `lg:`. Never write desktop-first overrides.

## Design Principles

- Interactive states are required Every clickable/focusable element must have `hover:`, `focus:ring-`, and `transition-colors` classes. 
- Never skip focus states — keyboard navigation depends on them.
- No inline styles Use Tailwind utilities only. Never use `style=""` attributes.
- No arbitrary values without justification Avoid `w-[372px]`, `mt-[13px]`, etc. Use spacing/sizing from the Tailwind scale.

## Conventions

- Extract repeated class strings into ViewComponents If the same Tailwind class combination appears in more than one place, extract it into a ViewComponent rather than copying the string.
- Semantic color palette Blue = primary actions, Green = success, Red = errors/destructive, Yellow = warnings, Gray = neutral/secondary. Don't deviate without a design reason.
- Accessibility checklist Icon-only buttons need `aria-label`. Navigation links need `aria-current` for the active page. Form inputs need associated `<label>` elements. Use `role="alert"` on flash/error messages.
- Custom utilities are a last resort Only add `@utility` rules to `application.css` when the pattern is used everywhere and can't reasonably live in a ViewComponent.