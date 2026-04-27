# Codex Instructions: test/avo

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/avo.md`

## Source: `claude/rules/avo.md`

# Avo Resources and Conventions

- Use the generator first: `bin/rails generate avo:resource model_name`.
- Resources live in the `Avo::Resources::` namespace and inherit from `Avo::BaseResource`.
- Declare fields unconditionally. Use `visible: -> { condition }` for conditional visibility instead of `if/else` inside `def fields`.
- Set `self.includes` when association fields are shown on index pages to avoid N+1 queries.
- Treat `required:` as cosmetic only; real validations belong on the model.
- If an association field is `searchable: true`, configure `self.search` on the target resource.
- Prefer view-specific field methods such as `display_fields`, `form_fields`, `index_fields`, `show_fields`, and `edit_fields` when different pages need different fields.
- Defer detailed Avo option semantics to the `avo-resources` skill and official Avo docs.
