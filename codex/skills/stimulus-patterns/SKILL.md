---
name: "stimulus-patterns"
description: "Stimulus controller patterns, lifecycle callbacks, targets, values, actions, composition, and reusable controller library. Reference material for Stimulus development."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: user-invocable. -->

# Stimulus Patterns

## Core Philosophy

**Stimulus for sprinkles, not frameworks.** Use Stimulus to add behavior to server-rendered HTML, not to build SPAs.

## Assumptions

Examples assume Rails with Hotwire and importmap. If the repo uses jsbundling, Vite, or another bundler, keep the controller patterns but follow the repo's JavaScript registration and package installation conventions.

### What Stimulus is for:
- Progressive enhancement (works without JS)
- DOM manipulation (show/hide, toggle, animate)
- Form enhancements (auto-submit, validation UI)
- UI interactions (dropdowns, modals, tooltips)
- Integration with libraries (Sortable, Trix, etc.)

### What Stimulus is NOT for:
- Business logic (belongs in models)
- Data fetching (use Turbo)
- Client-side routing (use Turbo)
- State management (server is source of truth)
- Replacing server-rendered views

### Controller size philosophy:
- 62% are reusable/generic (toggle, modal, clipboard)
- 38% are domain-specific (drag-and-drop cards)
- Most under 50 lines
- Single responsibility only

## Project Knowledge

**Tech Stack:** Stimulus 3.2+, Turbo 8+, Importmap (no bundler)
**Pattern:** One controller per file, small and focused, composed together
**Location:** `app/javascript/controllers/`

## Commands

- **Generate controller:** `bin/rails generate stimulus [name]`
- **List controllers:** `ls app/javascript/controllers/`
- **Test in browser:** Open DevTools console, check `this.application.controllers`
- **Debug:** Add `console.log()` in controller methods

## Stimulus Controller Structure

### Basic template

```javascript
// app/javascript/controllers/[name]_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  // Static properties
  static targets = ["input", "output"]
  static classes = ["active", "hidden"]
  static values = {
    url: String,
    timeout: { type: Number, default: 5000 }
  }

  // Lifecycle callbacks
  connect() {
    console.log("Controller connected", this.element)
  }

  disconnect() {
    // Cleanup
  }

  // Action methods (called from data-action)
  toggle(event) {
    event.preventDefault()
    this.element.classList.toggle(this.activeClass)
  }

  // Private methods (use # prefix)
  #helper() {
    return "private method"
  }
}
```

## Pattern Index

1. **Reusable UI Controllers** — Toggle, clipboard, auto-dismiss, modal, dropdown
2. **Form Enhancement Controllers** — Auto-submit, character counter, form validation UI
3. **Integration Controllers** — Sortable (drag-and-drop with SortableJS), Trix editor enhancements
4. **Tracking & Analytics Controllers** — Beacon (sendBeacon), IntersectionObserver visibility tracking
5. **Animation Controllers** — Slide-down (max-height transition), fade-in (opacity transition)
6. **Domain-Specific Controllers** — Card drag-and-drop, client-side filtering

## Naming Conventions

### Controller names
- Kebab-case in HTML: `data-controller="auto-submit"`
- Snake_case in filename: `auto_submit_controller.js`
- PascalCase in class: `AutoSubmitController`

### Targets
- camelCase: `data-[controller]-target="menuItem"`
- Access: `this.menuItemTarget` or `this.menuItemTargets`

### Values
- camelCase: `data-[controller]-url-value="/path"`
- Access: `this.urlValue`

### Classes
- camelCase: `data-[controller]-active-class="is-active"`
- Access: `this.activeClass`

## Common Stimulus Patterns Catalog

### 1. Toggle class
```javascript
toggle() {
  this.element.classList.toggle(this.activeClass)
}
```

### 2. Show on hover
```javascript
show() {
  this.element.classList.remove(this.hiddenClass)
}

hide() {
  this.element.classList.add(this.hiddenClass)
}
```

### 3. Disable button on submit
```javascript
submit() {
  this.submitTarget.disabled = true
  this.element.requestSubmit()
}
```

### 4. Confirm action
```javascript
confirm(event) {
  if (!window.confirm("Are you sure?")) {
    event.preventDefault()
  }
}
```

### 5. Prevent default
```javascript
prevent(event) {
  event.preventDefault()
}
```

## Reusable Controller Library

The approach creates a library of generic controllers:

**UI controllers:**
- `toggle_controller` - Show/hide elements
- `dropdown_controller` - Dropdown menus
- `modal_controller` - Dialog boxes
- `tabs_controller` - Tab navigation
- `tooltip_controller` - Tooltips

**Form controllers:**
- `auto_submit_controller` - Auto-submit forms
- `character_counter_controller` - Character counting
- `form_validation_controller` - Validation UI
- `password_visibility_controller` - Show/hide password

**Utility controllers:**
- `clipboard_controller` - Copy to clipboard
- `auto_dismiss_controller` - Auto-remove elements
- `confirm_controller` - Confirmation dialogs
- `disable_controller` - Disable buttons

**Integration controllers:**
- `sortable_controller` - Drag and drop
- `trix_controller` - Rich text editor
- `flatpickr_controller` - Date picker

**Tracking controllers:**
- `beacon_controller` - Track events
- `visibility_controller` - Track visibility
- `scroll_controller` - Track scrolling

## Performance Tips

### 1. Use event delegation
```javascript
connect() {
  this.element.addEventListener("click", this.#handleClick)
}

#handleClick(event) {
  if (event.target.matches(".delete-button")) {
    this.delete(event)
  }
}
```

### 2. Debounce expensive operations
```javascript
import { debounce } from "./helpers"

connect() {
  this.search = debounce(this.search.bind(this), 300)
}

search(event) {
  // Expensive operation
}
```

### 3. Clean up in disconnect
```javascript
disconnect() {
  clearTimeout(this.timeout)
  this.observer?.disconnect()
  document.removeEventListener("click", this.boundClose)
}
```

### 4. Use IntersectionObserver for visibility
```javascript
connect() {
  this.observer = new IntersectionObserver(this.#handleIntersection)
  this.observer.observe(this.element)
}
```

## Boundaries

- **Always do:** Keep controllers small (under 50 lines), single responsibility only, use values/classes for configuration, clean up in disconnect(), use private methods (#), provide fallback for no-JS, test with system tests, use event delegation
- **Ask first:** Before adding business logic (belongs in models), before fetching data (use Turbo), before managing complex state (server is source), before creating domain-specific controllers (favor generic + composition)
- **Never do:** Build SPAs with Stimulus, put business logic in controllers, manage application state client-side, skip disconnect() cleanup, hardcode values (use data-values), create god controllers (split them), forget CSRF tokens in fetch requests, skip progressive enhancement (must work without JS)

## Additional Resources

- [Detailed controller examples](reference/controllers.md) — Full implementations for all 6 pattern categories, composition patterns, and testing examples

## Agent Verification

- Run focused system tests for the interaction or add one if the behavior is user-facing.
- Manually smoke the controller in a browser when targets, values, lifecycle cleanup, or third-party libraries are involved.
- Check that the no-JS fallback still works for progressive enhancement.
