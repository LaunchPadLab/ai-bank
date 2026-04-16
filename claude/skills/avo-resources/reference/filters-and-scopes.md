# Avo Filters & Scopes Reference

Avo provides two filtering mechanisms: **basic filters** (one filter per file, four types) and **dynamic filters** (field-level `filterable` option with composable conditions). Resources can also use **scopes** for quick data segmentation.

---

## Basic Filters

### Filter Types

Avo ships four basic filter types, each inheriting from a base class:

| Type | Base Class | Value Type | Generator Flag |
|------|-----------|------------|----------------|
| Boolean | `Avo::Filters::BooleanFilter` | Hash `{ key: true/false }` | `--type boolean` (default) |
| Select | `Avo::Filters::SelectFilter` | Single string | `--type select` |
| Multiple Select | `Avo::Filters::MultipleSelectFilter` | Array of strings | `--type multiple_select` |
| Text | `Avo::Filters::TextFilter` | String | `--type text` |
| DateTime | `Avo::Filters::DateTimeFilter` | String (date/time) | `--type date_time` |

### Generating Filters

```bash
bin/rails generate avo:filter featured                      # BooleanFilter (default)
bin/rails generate avo:filter published --type select       # SelectFilter
bin/rails generate avo:filter post_status --type multiple_select
bin/rails generate avo:filter name --type text
bin/rails generate avo:filter created_at --type date_time
```

### Boolean Filter

```ruby
# app/avo/filters/featured.rb
class Avo::Filters::Featured < Avo::Filters::BooleanFilter
  self.name = "Featured filter"

  # `values` is a Hash with stringified keys: { "is_featured" => true, "is_unfeatured" => false }
  def apply(request, query, values)
    return query if values["is_featured"] && values["is_unfeatured"]

    if values["is_featured"]
      query = query.where(is_featured: true)
    elsif values["is_unfeatured"]
      query = query.where(is_featured: false)
    end

    query
  end

  def options
    {
      is_featured: "Featured",
      is_unfeatured: "Unfeatured"
    }
  end

  def default
    { is_featured: true }
  end
end
```

### Select Filter

```ruby
# app/avo/filters/published.rb
class Avo::Filters::Published < Avo::Filters::SelectFilter
  self.name = "Published status"

  # `value` is a single string: "published" or "unpublished"
  def apply(request, query, value)
    case value
    when "published"
      query.where.not(published_at: nil)
    when "unpublished"
      query.where(published_at: nil)
    else
      query
    end
  end

  def options
    {
      published: "Published",
      unpublished: "Unpublished"
    }
  end

  def default
    :published
  end
end
```

### Multiple Select Filter

```ruby
# app/avo/filters/post_status.rb
class Avo::Filters::PostStatus < Avo::Filters::MultipleSelectFilter
  self.name = "Status"

  # `value` is an array of strings: ["admins", "non_admins"]
  def apply(request, query, value)
    query = query.admins if value.include?("admins")
    query = query.non_admins if value.include?("non_admins")
    query
  end

  def options
    {
      admins: "Admins",
      non_admins: "Non admins"
    }
  end
end
```

### Text Filter

```ruby
# app/avo/filters/name.rb
class Avo::Filters::Name < Avo::Filters::TextFilter
  self.name = "Name filter"
  self.button_label = "Filter by name"

  # `value` is a plain string: "avo"
  def apply(request, query, value)
    query.where("LOWER(name) LIKE ?", "%#{value}%")
  end
end
```

### DateTime Filter

```ruby
# app/avo/filters/starting_at.rb
class Avo::Filters::StartingAt < Avo::Filters::DateTimeFilter
  self.name = "The starting at filter"
  self.button_label = "Filter by start time"
  self.empty_message = "Search by start time"
  self.type = :time       # :date, :time, or :date_time (default)
  self.mode = :single     # :single or :range (default)

  def picker_options(value)
    super.merge({ minuteIncrement: 3 })
  end

  def apply(request, query, value)
    query.where("to_char(starting_at, 'HH24:MI:SS') = ?", value)
  end
end
```

For `:range` mode, split the value: `date_1, date_2 = value.split(" to ")`.

### Registering Filters on a Resource

```ruby
class Avo::Resources::Post < Avo::BaseResource
  def filters
    filter Avo::Filters::Published
    filter Avo::Filters::Featured
  end
end
```

### Filter Options

| Option | Description |
|--------|-------------|
| `self.name` | Display name (string or lambda) |
| `self.button_label` | Button label text (string or lambda) |
| `self.visible` | Lambda controlling visibility (returns boolean) |
| `self.empty_message` | Message when no options are available |
| `apply` | Method receiving `(request, query, value/values)` |
| `options` | Method returning available options hash |
| `default` | Method returning default state |
| `react` | Method to react to other filters' values |

### Filter Visibility

```ruby
self.visible = -> do
  # Available: block, context, current_user, params,
  #            parent_model, parent_resource, resource, view, view_context
  current_user.admin?
end
```

### Filter Arguments

Pass arguments from the resource to customize filter behavior:

```ruby
# Resource
def filters
  filter Avo::Filters::NameFilter, arguments: { case_insensitive: true }
end

# Filter — arguments available in apply, options, and visible
class Avo::Filters::NameFilter < Avo::Filters::TextFilter
  self.visible = -> { arguments[:case_insensitive] }

  def apply(request, query, value)
    if arguments[:case_insensitive]
      query.where("LOWER(name) LIKE ?", "%#{value.downcase}%")
    else
      query.where("name LIKE ?", "%#{value}%")
    end
  end
end
```

### Dynamic Filter Options (Reacting Between Filters)

Filters can depend on each other via `applied_filters`:

```ruby
class Avo::Filters::CourseCity < Avo::Filters::BooleanFilter
  self.name = "Course city filter"
  self.empty_message = "Please select a country to view options."

  def apply(request, query, values)
    query.where(city: values.select { |_, selected| selected }.keys)
  end

  def options
    cities_for_countries(countries)
  end

  def react
    if applied_filters["Avo::Filters::CourseCountryFilter"].present? &&
       applied_filters["Avo::Filters::CourseCityFilter"].blank?
      selected = applied_filters["Avo::Filters::CourseCountryFilter"]
                   .select { |_, selected| selected }
      cities = cities_for_countries(selected.keys)
      [[cities.first.first, true]].to_h
    end
  end

  private

  def cities_for_countries(countries_array = [])
    countries_array
      .map { |country| Course.cities.stringify_keys[country] }
      .flatten
      .map { |city| [city, city] }
      .to_h
  end

  def countries
    filter = applied_filters["Avo::Filters::CourseCountryFilter"]
    return [] unless filter.present?

    filter.select { |_, selected| selected }.keys
  end
end
```

### Filter URL Encoding Helpers

```ruby
# Rails view helpers
decode_filter_params(params[:filters])
encode_filter_params({ "NameFilter" => "Apple" })

# Standalone helpers (usable anywhere)
Avo::Filters::BaseFilter.decode_filters(params[:filters])
Avo::Filters::BaseFilter.encode_filters({ "Avo::Filters::NameFilter" => "Apple" })
```

---

## Dynamic Filters (Advanced license)

Dynamic filters use ransack and the `filterable: true` field option. Multiple conditions per attribute, composable by the user.

### Setup

```ruby
class Avo::Resources::Project < Avo::BaseResource
  def fields
    field :status, as: :status, filterable: true
    field :stage, as: :badge, filterable: true
    field :country, as: :country, filterable: true
  end
end

# Model — authorize ransackable attributes
class Project < ApplicationRecord
  def self.ransackable_attributes(auth_object = nil)
    ["status", "stage", "country"]
  end
end
```

### Filter Combination Logic

- Filters on the **same** attribute → combined with **OR**
- Filters on **different** attributes → combined with **AND**

### Custom Dynamic Filters

Two definition approaches:

```ruby
# 1. Via field's filterable hash
field :first_name, as: :text, filterable: {
  label: "Name",
  icon: "heroicons/outline/user",
  type: :text,
  conditions: { contains: "Contains", is: "Equals" }.invert,
  query: -> {
    case filter_param.condition.to_sym
    when :contains
      query.where("name ILIKE ?", "%#{filter_param.value}%")
    when :is
      query.where(name: filter_param.value)
    end
  }
}

# 2. Via dynamic_filter method (can be independent of fields)
def filters
  dynamic_filter :first_name,
    type: :text,
    label: "Name",
    conditions: { contains: "Contains", is: "Equals" }.invert,
    query: -> {
      case filter_param.condition.to_sym
      when :contains
        query.where("name ILIKE ?", "%#{filter_param.value}%")
      when :is
        query.where(name: filter_param.value)
      end
    }
end
```

### Dynamic Filter Options

| Option | Description |
|--------|-------------|
| `label` | Custom display label |
| `icon` | Heroicon identifier |
| `type` | `:boolean`, `:date`, `:date_time`, `:time`, `:number`, `:select`, `:text`, `:tags` |
| `query` | Lambda with access to `query`, `filter_param` (id, condition, value) |
| `conditions` | Hash of conditions (use `{}` to hide dropdown) |
| `query_attributes` | DB column(s) to query (symbol or array) |
| `suggestions` | Array of strings or lambda for text input hints |
| `options` | Array or hash for select type filters |
| `render_apply_button` | Boolean, hide apply button with `false` |
| `apply_on_select` | Boolean, auto-apply on value change |

### Dynamic Filter Configuration

```ruby
if defined?(Avo::DynamicFilters)
  Avo::DynamicFilters.configure do |config|
    config.button_label = "Advanced filters"
    config.always_expanded = true
  end
end
```

---

## Resource Scopes (Advanced license)

Scopes segment data on the index view with clickable tabs.

### Generating Scopes

```bash
bin/rails generate avo:scope admins
```

### Scope Definition

```ruby
# app/avo/scopes/admins.rb
class Avo::Scopes::Admins < Avo::Advanced::Scopes::BaseScope
  self.name = "Admins"
  self.description = "Admins only"
  self.scope = :admins                   # references model scope
  self.visible = -> { true }
end

# app/models/user.rb
class User < ApplicationRecord
  scope :admins, -> { where(role: :admin) }
end
```

### Registering Scopes

```ruby
# app/avo/resources/user.rb
class Avo::Resources::User < Avo::BaseResource
  def scopes
    scope Avo::Scopes::Admins
    scope Avo::Scopes::EvenId, default: true
  end
end
```

### Scope Options

| Option | Description |
|--------|-------------|
| `self.name` | Display name (string or lambda with `scoped_query` access) |
| `self.description` | Tooltip text (string or lambda) |
| `self.scope` | Symbol (model scope) or lambda with `query` access |
| `self.visible` | Lambda for visibility (has `parent_record`, `parent_resource`) |

### Scope with Count

```ruby
class Avo::Scopes::EvenId < Avo::Advanced::Scopes::BaseScope
  self.name = -> { "Even (#{scoped_query.count})" }
  self.description = -> { "Only #{resource.name.downcase.pluralize} that have an even ID" }
  self.scope = -> { query.where("#{resource.model_key}.id % 2 = ?", "0") }
  self.visible = -> { current_user.admin? }
end
```

### Default Scope

```ruby
def scopes
  scope Avo::Scopes::OddId
  scope Avo::Scopes::EvenId, default: true
  # Or with a proc:
  scope Avo::Scopes::EvenId, default: -> { current_user.admin? }
end
```

### Removing the "All" Scope

```ruby
def scopes
  remove_scope_all
  scope Avo::Scopes::Admins
end
```
