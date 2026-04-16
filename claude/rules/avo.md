---
paths:
  - "app/avo/**/*.erb"
  - "test/avo/**/*.rb"
  - "app/views/avo/**/*.erb"
  - "app/controllers/avo/**/*.rb"
  - "test/controllers/avo/**/*.rb"
---

# Avo Resources and Coventions

- Never use `if/else` inside def fields Always declare all fields unconditionally. Use `visible: -> { condition }` to control visibility. Using if inside `def fields` breaks Avo's field discovery.
- Always set `self.includes` for associations Any resource with association fields (`belongs_to`, `has_many`, etc.) must declare `self.includes` to avoid N+1 queries on the index view.
- `required:` is cosmetic only The `required:` option only adds an asterisk — it does not add a validation. Real validation must live on the model.
- `searchable: true` on association fields requires `self.search` on the target resource If you add `searchable: true` to a `belongs_to` or `has_many`, the linked resource must have `self.search` configured.
- Resources live in `Avo::Resources::` namespace Classes must be class `Avo::Resources::ModelName < Avo::BaseResource`, not bare `ModelNameResource`.
- Use view-specific field methods for complex resources Prefer `display_fields`/`form_fields` (or `index_fields`/`show_fields`/`edit_fields`) over a single fields method when Index/Show needs different fields than New/Edit.
- Use the generator first Always run `bin/rails generate avo:resource model_name` as the starting point — it auto-detects model fields. Don't write resources from scratch.

