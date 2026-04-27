---
name: avo-resources
description: Creates and configures Avo 3.x resources for Ruby on Rails admin panels. Use proactively when creating new Avo resources, adding fields to resources, configuring resource options, setting up associations in Avo, working with any file in app/avo/resources/, generating Avo resources from models, or when the user mentions Avo resources, Avo fields, Avo admin, or CRUD in the context of Avo.
argument-hint: "[model-name]"
---

# Avo 3.x Resources

**Model to create resource for: $ARGUMENTS**

## Canonical Documentation

Primary Avo reference for this skill:
`https://docs.avohq.io/3.0/llms-full.txt`

Use the Avo LLM docs as the source of truth for Avo-specific APIs, DSL options,
and framework behavior. Consult them before making Avo-specific decisions about:

- resource DSL, field types, and field options
- associations, actions, filters, scopes, and search
- authorization, customization, and view behavior
- version-specific Avo 3.x capabilities and best practices

Prefer this skill for workflow and project-specific guidance. Prefer the Avo LLM
docs when you need authoritative Avo semantics or option details. If this skill
conflicts with the Avo docs, follow the Avo docs.

## Existing Avo Resources
- List `app/avo/resources/` to inspect existing resources, if the directory exists.
- List `app/avo/actions/` to inspect existing actions, if the directory exists.
- List `app/avo/filters/` to inspect existing filters, if the directory exists.

## Resource Structure

Resources live in `app/avo/resources/` and inherit from `Avo::BaseResource`. Each resource maps to a Rails model.

```ruby
# app/avo/resources/post.rb
class Avo::Resources::Post < Avo::BaseResource
  self.title = :name
  self.includes = [:user, :tags]
  self.description = "Blog posts managed by the team."

  def fields
    field :id, as: :id, link_to_record: true
    field :name, as: :text, required: true
    field :body, as: :trix, placeholder: "Add the post body here"
    field :cover_photo, as: :file, is_image: true
    field :is_featured, as: :boolean
    field :status, as: :select, enum: ::Post.statuses
    field :user, as: :belongs_to
    field :comments, as: :has_many
    field :tags, as: :tags
  end
end
```

### Key class attributes

- `self.title` — Record label: symbol (`:name`), method name, or lambda (`-> { record.full_name }`)
- `self.includes` — Eager-load associations: `[:user, :tags]`
- `self.model_class` — Override inferred model: `"Delayed::Job"`
- `self.description` — Text shown on views (string or lambda with access to `view`, `record`)
- `self.visible_on_sidebar` — Show/hide in auto-generated sidebar menu

## Field Declaration

```ruby
field :name, as: :text, required: true, placeholder: "John"
```

### Common field options

| Option | Description |
|--------|-------------|
| `name:` | Custom label: `name: "Availability"` |
| `required:` | Asterisk indicator (bool or lambda, cosmetic only) |
| `readonly:` | Renders disabled, still submits value |
| `disabled:` | Renders disabled, value NOT submitted (bool or lambda) |
| `placeholder:` | Input placeholder on forms |
| `help:` | Help text below the field (string or HTML) |
| `visible:` | Conditionally show/hide (bool or lambda) |
| `hide_on:` | `:index`, `:show`, `:forms`, `:display`, `:all` |
| `show_on:` / `only_on:` / `except_on:` | View visibility control |
| `sortable:` | Enable column sorting on Index (bool or lambda) |
| `default:` | Default value on New view (value or lambda) |
| `nullable:` | Store NULL instead of empty string |
| `link_to_record:` | Make field a clickable link to the record |
| `filterable:` | Enable built-in column filtering |

### Best practice: use `visible` instead of `if/else`

```ruby
# WRONG — breaks Avo's field discovery
def fields
  if params[:special_case].present?
    field :special_field, as: :text
  end
end

# CORRECT — always declare all fields
def fields
  field :special_field, as: :text, visible: -> { params[:special_case].present? }
  field :regular_field, as: :text, visible: -> { params[:special_case].blank? }
end
```

## Field Types Quick Reference

### Basic fields

| Type | Declaration | Notes |
|------|-------------|-------|
| ID | `as: :id` | Auto-hidden on forms |
| Text | `as: :text` | Single-line string |
| Textarea | `as: :textarea` | Multi-line, `rows:` option |
| Number | `as: :number` | Integers and floats |
| Password | `as: :password` | Masked input |
| Boolean | `as: :boolean` | Checkbox |
| Select | `as: :select` | Requires `options:` or `enum:` |
| Date | `as: :date` | Date picker |
| DateTime | `as: :date_time` | Date + time, `timezone:` and `format:` |
| Time | `as: :time` | Time-only picker |
| Hidden | `as: :hidden` | Hidden form field with `default:` |

### Rich content fields

| Type | Declaration | Notes |
|------|-------------|-------|
| Trix | `as: :trix` | Rich text editor |
| Markdown | `as: :markdown` | Markdown editor with preview |
| Code | `as: :code` | Code editor (`language:`, `theme:`) |
| Rhino | `as: :rhino` | WYSIWYG (Tiptap-based) |

### Specialized fields

| Type | Declaration | Notes |
|------|-------------|-------|
| File / Files | `as: :file` / `as: :files` | Active Storage (`is_image:`) |
| Gravatar | `as: :gravatar` | Email-based avatar |
| External Image | `as: :external_image` | URL-based image |
| Boolean Group | `as: :boolean_group` | Multiple checkboxes (`options:` hash) |
| Key Value | `as: :key_value` | JSON key-value editor |
| Tags | `as: :tags` | Tag input |
| Badge | `as: :badge` | Status badge (`map:`) |
| Status | `as: :status` | `failed_when:`, `loading_when:` |
| Country | `as: :country` | Country selector |
| Location | `as: :location` | Map coordinates |
| Heading | `as: :heading` | Section divider (display only) |
| Record Link | `as: :record_link` | Link to another record |
| Radio | `as: :radio` | Radio button group |
| Money | `as: :money` | Currency (requires `money-rails`) |

### Association fields

| Type | Declaration | Notes |
|------|-------------|-------|
| Belongs To | `as: :belongs_to` | Dropdown or searchable select |
| Has One | `as: :has_one` | Inline show view of related record |
| Has Many | `as: :has_many` | Table of related records on Show |
| HABTM | `as: :has_and_belongs_to_many` | Many-to-many with attach/detach |

## View-Specific Fields

Instead of one `def fields`, define view-specific methods:

```ruby
class Avo::Resources::User < Avo::BaseResource
  def display_fields   # Index + Show
    field :id, as: :id
    field :name, as: :text
    field :email, as: :text
  end

  def form_fields      # New + Edit
    field :name, as: :text, required: true
    field :email, as: :text, required: true
    field :bio, as: :markdown
  end
end
```

**Precedence:** `index_fields` > `display_fields` > `fields`. Same for `edit_fields` > `form_fields` > `fields`.

Available: `index_fields`, `show_fields`, `edit_fields`, `new_fields`, `display_fields`, `form_fields`, `fields` (fallback).

## Computed Fields

Use a block to compute values not stored in the database. Computed fields display on Index and Show views only.

```ruby
field :is_published, as: :boolean do
  record.published_at.present?
end

field :full_name, as: :text do
  "#{record.first_name} #{record.last_name}"
end

field :post_count, as: :number do
  record.posts.count
end
```

## Field Formatting

```ruby
field :is_writer, as: :text, format_using: -> {
  view.form? ? value : (value.present? ? "Yes" : "No")
}

field :price, as: :number, format_using: -> { view_context.number_to_currency(value) }

field :status, as: :text, format_display_using: -> { value.titleize }

field :metadata, as: :code, update_using: -> { ActiveSupport::JSON.decode(value) }
```

View-specific: `format_index_using`, `format_show_using`, `format_edit_using`, `format_new_using`, `format_form_using`, `format_display_using`. Use `update_using` to parse values before saving.

## Association Fields

### `belongs_to`

```ruby
field :user, as: :belongs_to
field :user, as: :belongs_to, searchable: true
field :user, as: :belongs_to, attach_scope: -> { query.non_admins }
field :commentable, as: :belongs_to, polymorphic_as: :commentable, types: [::Post, ::Project]
```

Options: `searchable`, `attach_scope`, `polymorphic_as`, `types`, `can_create`, `use_resource`.

### `has_many` / `has_one` / `has_and_belongs_to_many`

```ruby
field :comments, as: :has_many
field :comments, as: :has_many, searchable: true
field :comments, as: :has_many, scope: -> { query.approved }
field :users, as: :has_many, use_resource: Avo::Resources::TeamUser
field :admin, as: :has_one
field :tags, as: :has_and_belongs_to_many
```

Options: `searchable`, `scope` (filters displayed records), `attach_scope` (filters attach modal), `use_resource`, `name`, `description`.

When using `searchable: true`, the target resource **must** have `self.search` configured.

## Actions Quick Start

```ruby
class Avo::Actions::TogglePublished < Avo::BaseAction
  self.name = "Toggle Published"
  # self.standalone = true  # uncomment for actions without record selection

  def fields
    field :notify_user, as: :boolean
    field :message, as: :textarea
  end

  def handle(query:, fields:, current_user:, resource:, **args)
    query.each do |record|
      record.update!(published: !record.published)
    end
    succeed "Toggled #{query.count} records."
  end
end
```

Register on a resource:

```ruby
def actions
  action Avo::Actions::TogglePublished
  action Avo::Actions::ExportPosts, arguments: { format: :csv }
end
```

Feedback methods: `succeed`, `warn`, `inform`, `error`, `silent` (each accepts optional `timeout:`).

## Filters Quick Start

### Boolean filter

```ruby
class Avo::Filters::Featured < Avo::Filters::BooleanFilter
  self.name = "Featured filter"

  def apply(request, query, values)
    if values["is_featured"]
      query = query.where(is_featured: true)
    elsif values["is_unfeatured"]
      query = query.where(is_featured: false)
    end
    query
  end

  def options
    { is_featured: "Featured", is_unfeatured: "Unfeatured" }
  end
end
```

### Select filter

```ruby
class Avo::Filters::Published < Avo::Filters::SelectFilter
  self.name = "Published status"

  def apply(request, query, value)
    case value
    when "published"  then query.where.not(published_at: nil)
    when "unpublished" then query.where(published_at: nil)
    else query
    end
  end

  def options
    { published: "Published", unpublished: "Unpublished" }
  end
end
```

### Register on a resource

```ruby
def filters
  filter Avo::Filters::Published
  filter Avo::Filters::Featured
end
```

Other filter types: `TextFilter`, `DateTimeFilter`, `MultipleSelectFilter`.

## Resource Scopes (Advanced license)

```ruby
class Avo::Scopes::Admins < Avo::Advanced::Scopes::BaseScope
  self.name = "Admins"
  self.description = "Admins only"
  self.scope = :admins        # must match a model scope
  self.visible = -> { true }
end
```

```ruby
def scopes
  scope Avo::Scopes::Admins
  scope Avo::Scopes::Active, default: true
end
```

## Resource Options

### Search

```ruby
class Avo::Resources::User < Avo::BaseResource
  self.search = {
    query: -> { query.ransack(name_cont: q, email_cont: q, m: "or").result(distinct: false) }
  }
end
```

Requires the `ransack` gem. The `q` variable contains the search query string.

### Ordering (with `acts_as_list` or similar)

```ruby
self.ordering = {
  visible_on: :index,  # or :association, or [:index, :association]
  display_inline: true,
  actions: {
    higher: -> { record.move_higher },
    lower: -> { record.move_lower },
    to_top: -> { record.move_to_top },
    to_bottom: -> { record.move_to_bottom }
  }
}
```

### Pagination and sorting

```ruby
self.pagination = { type: :countless, size: [1, 2, 2, 1] }
self.default_sort_column = :last_name
self.default_sort_direction = :asc
```

### Custom find method

For `friendly_id`, `prefix_id`, or custom `to_param`:

```ruby
self.find_record_method = -> {
  if id.is_a?(Array)
    query.where(slug: id)
  else
    query.friendly.find(id)
  end
}
```

### Custom index query

```ruby
self.index_query = -> { query.unscoped }
```

### Other options

- `self.after_create_path = :index` — redirect after create (`:show`, `:edit`, `:index`)
- `self.record_selector = false` — hide row checkboxes
- `self.confirm_on_save = true` — confirmation dialog before save
- `self.default_view_type = :grid` — `:table` (default), `:grid`, `:map`
- `self.devise_password_optional = true` — skip password validation on update

## Generator Commands

```bash
bin/rails generate avo:resource post                          # auto-detects model fields
bin/rails generate avo:resource mini_post --model-class post  # explicit model
bin/rails generate avo:all_resources                          # all models at once
bin/rails generate avo:action toggle_published                # action
bin/rails generate avo:action generate_report --standalone    # standalone action
bin/rails generate avo:filter featured                        # boolean filter (default)
bin/rails generate avo:filter published --type select         # select filter
bin/rails generate avo:scope admins                           # scope (Advanced)
bin/rails generate avo:controller posts                       # custom controller
```

## Additional Resources

- [reference/fields.md](reference/fields.md) -- All 30+ field types with options and code examples
- [reference/actions.md](reference/actions.md) -- Actions, standalone actions, response types, arguments
- [reference/filters-and-scopes.md](reference/filters-and-scopes.md) -- Boolean/select/text/dynamic filters, resource scopes
- [reference/authorization.md](reference/authorization.md) -- Pundit policies, association policies, attachment auth
- [reference/associations.md](reference/associations.md) -- belongs_to, has_many, has_one, scoping, attach/detach
- [reference/customization.md](reference/customization.md) -- Custom fields, tools, Stimulus, controls, branding
- [reference/search-and-menu.md](reference/search-and-menu.md) -- Search, menu editor, panels, tabs, sidebar
- [reference/testing.md](reference/testing.md) -- System tests, policy tests, action tests, Avo::Current
- [reference/configuration.md](reference/configuration.md) -- Initializer, routing, auth, licensing, pagination
