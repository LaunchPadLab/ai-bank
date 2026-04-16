# Avo Customization Reference

Comprehensive guide to customizing Avo admin panels: custom fields, resource tools, custom pages, Stimulus integration, controls, cover/profile photos, eject command, branding, TailwindCSS, and panel/sidebar layout.

---

## Custom Fields

Generate a custom field when built-in fields don't cover your needs. Each field has three view components (Edit, Show, Index) and a configuration file.

### Generate a Custom Field

```bash
bin/rails generate avo:field progress_bar
```

Creates:
- `app/avo/fields/progress_bar_field.rb` — field configuration
- `app/components/avo/fields/progress_bar_field/edit_component.{rb,html.erb}`
- `app/components/avo/fields/progress_bar_field/show_component.{rb,html.erb}`
- `app/components/avo/fields/progress_bar_field/index_component.{rb,html.erb}`

### Field Configuration with Options

```ruby
# app/avo/fields/progress_bar_field.rb
class Avo::Fields::ProgressBarField < Avo::Fields::BaseField
  attr_reader :max, :step, :display_value, :value_suffix

  def initialize(name, **args, &block)
    super(name, **args, &block)
    @max = args[:max] || 100
    @step = args[:step] || 1
    @display_value = args[:display_value] || false
    @value_suffix = args[:value_suffix] || nil
  end
end
```

### Using the Custom Field

```ruby
# app/avo/resources/project.rb
class Avo::Resources::Project < Avo::BaseResource
  def fields
    field :id, as: :id, link_to_record: true
    field :progress, as: :progress_bar, max: 100, step: 5, display_value: true, value_suffix: "%"
  end
end
```

### Duplicate an Existing Field as Template

```bash
bin/rails generate avo:field super_text --field_template text
```

### View Component Templates

```erb
<%# edit_component.html.erb %>
<%= edit_field_wrapper field: @field, index: @index, form: @form, resource: @resource,
      displayed_in_modal: @displayed_in_modal do %>
  <%= @form.text_field @field.id,
    class: helpers.input_classes("w-full", has_error: @field.model_errors.include?(@field.id)),
    placeholder: @field.placeholder,
    disabled: @field.readonly %>
<% end %>

<%# show_component.html.erb %>
<%= show_field_wrapper field: @field, index: @index do %>
  <%= @field.value %>
<% end %>

<%# index_component.html.erb %>
<%= index_field_wrapper field: @field do %>
  <%= @field.value %>
<% end %>
```

---

## Resource Tools (Custom Partials on Show/Edit Pages)

Resource tools let you embed custom Rails partials directly within a resource's show or edit page, alongside standard Avo fields.

```ruby
class Avo::Resources::User < Avo::BaseResource
  def fields
    field :id, as: :id
    field :name, as: :text

    tool UserTimeline
  end
end
```

The tool references a standard Rails partial or ViewComponent that renders inline with the resource.

---

## Custom Tools (Standalone Pages)

Custom tools are standalone pages within Avo, backed by their own controller actions and views.

### Generate a Custom Tool

```bash
bin/rails generate avo:tool dashboard
```

Creates:
- `app/controllers/avo/tools_controller.rb` — controller with action
- `app/views/avo/tools/dashboard.html.erb` — the view
- `app/views/avo/sidebar/items/_dashboard.html.erb` — sidebar link
- Route in `config/routes.rb`

### Controller

```ruby
class Avo::ToolsController < Avo::ApplicationController
  helper HomeHelper

  def dashboard
    @page_title = "Dashboard"
    add_breadcrumb "Dashboard"
  end
end
```

### View Template

```erb
<%# app/views/avo/tools/dashboard.html.erb %>
<div class="flex flex-col">
  <%= render Avo::PanelComponent.new title: "Dashboard", display_breadcrumbs: true do |c| %>
    <% c.with_tools do %>
      <div class="text-sm italic">Panel tools section</div>
    <% end %>

    <% c.with_body do %>
      <div class="flex flex-col justify-between py-6 min-h-24">
        <div class="px-6 space-y-4">
          <h3>Welcome to the dashboard</h3>
        </div>
      </div>
    <% end %>
  <% end %>
</div>
```

### Route Setup

```ruby
# config/routes.rb
Rails.application.routes.draw do
  namespace :avo do
    get "dashboard", to: "tools#dashboard"
  end

  authenticate :user, ->(user) { user.admin? } do
    mount_avo
  end
end
```

### Path Helpers

- Avo paths: `avo.resources_posts_path(1)` (prefix with `avo.`)
- Main app paths: `main_app.posts_path` (prefix with `main_app.`)

---

## Stimulus JS Integration

StimulusJS is deeply integrated into Avo's CRUD UI. You can extend it with your own Stimulus controllers.

Add custom JavaScript via the ejected `_scripts.html.erb` partial:

```bash
bin/rails generate avo:eject --partial :scripts
```

---

## Customizable Controls

Override the default buttons on Show, Edit, Index, and Row views.

### Default Controls

```ruby
# show controls
back_button; delete_button; detach_button; actions_list; edit_button

# form (edit & new) controls
back_button; delete_button; actions_list; save_button

# index controls
attach_button; actions_list; create_button

# row controls
order_controls; show_button; edit_button; detach_button; delete_button
```

### Show Controls

```ruby
class Avo::Resources::Fish < Avo::BaseResource
  self.show_controls = -> do
    back_button label: "", title: "Go back now"
    link_to "Fish.com", "https://fish.com", icon: "heroicons/outline/academic-cap", target: :_blank
    delete_button label: "", title: "Delete"
    detach_button label: "", title: "Detach"
    actions_list label: "Runnables", exclude: [ReleaseFish], style: :primary, color: :slate
    action Avo::Actions::ReleaseFish, style: :primary, color: :fuchsia, icon: "heroicons/outline/globe"
    edit_button label: ""
  end
end
```

### Edit Controls

```ruby
self.edit_controls = -> do
  back_button label: "", title: "Go back now"
  delete_button label: "", title: "Delete"
  actions_list exclude: [Avo::Actions::ReleaseFish], style: :primary, color: :slate
  action Avo::Actions::ReleaseFish, style: :primary, color: :fuchsia if view != :new
  save_button label: "Save Fish"
end
```

### Index Controls

```ruby
self.index_controls = -> do
  link_to "Fish.com", "https://fish.com", icon: "heroicons/outline/academic-cap", target: :_blank
  actions_list exclude: [Avo::Actions::DummyAction], style: :primary, color: :slate
  attach_button label: "Attach one Fish"
  create_button label: "Create a new Fish"
end
```

### Row Controls

```ruby
self.row_controls = -> do
  action Avo::Actions::ReleaseFish, label: "Release #{record.name}", style: :primary, color: :blue,
    icon: "heroicons/outline/hand-raised" unless params[:view_type] == "grid"
  edit_button title: "Edit this Fish now!"
  show_button title: "Show this Fish now!"
  delete_button title: "Delete", confirmation_message: "Are you sure?"
  actions_list style: :primary, color: :slate, label: "Actions"
end
```

### Control Types

| Control | Supported Options | Notes |
|---------|------------------|-------|
| `back_button` | label, title, style, color, icon | Computed hierarchical navigation |
| `delete_button` | label, title, style, color, icon | Respects authorization policies |
| `detach_button` | label, title, style, color, icon | Visible on `has_one` associations |
| `edit_button` | label, title, style, color, icon | Links to edit page |
| `save_button` | label, title, style, color, icon | Form submit |
| `show_button` | label, title, style, color, icon | Links to show page |
| `actions_list` | label, title, style, color, icon, include, exclude | Dropdown of actions |
| `action` | title, style, color, icon, arguments | Single action button |
| `link_to` | title, style, color, icon, target, data, class | Custom link |
| `list` | label, title, style, color, icon | Dropdown of links and actions |

### `actions_list` Include/Exclude

```ruby
actions_list exclude: [Avo::Actions::ExportSelection, Avo::Actions::PublishPost]
actions_list include: [Avo::Actions::DisableAccount]
```

### List Control (Dropdown)

```ruby
list label: "Custom List", icon: "heroicons/outline/cube-transparent", style: :primary do
  link_to "Google", "https://google.com", icon: "heroicons/outline/academic-cap"
  action Avo::Actions::Sub::DummyAction, icon: "heroicons/outline/globe"
  divider
  link_to "Fish.com", "https://fish.com", icon: "heroicons/outline/fire", target: :_blank
end
```

### Using `default_controls`

Add links before/after the default controls without re-declaring them all:

```ruby
self.show_controls = -> do
  link_to "View on site", post_path(record), target: :_blank
  default_controls
end
```

### Conditional Actions in Controls

```ruby
self.show_controls = -> do
  back_button label: ""
  action Avo::Actions::ReleaseFish, style: :primary if record.something?
  edit_button label: ""
end
```

### Control Style Options

| Option | Values |
|--------|--------|
| `style` | `:primary`, `:outline`, `:text`, `:icon` |
| `color` | Any Tailwind color as symbol (`:slate`, `:fuchsia`, `:blue`, etc.) |
| `icon` | `"heroicons/outline/academic-cap"`, `"heroicons/solid/adjustments"` |
| `target` | `:_blank`, `:_top`, `:_self` |

---

## Cover and Profile Photos

### Profile Photo

```ruby
class Avo::Resources::User < Avo::BaseResource
  self.profile_photo = {
    visible_on: [:show, :forms],     # default: [:show, :forms]
    source: -> {
      if view.index?
        DEFAULT_IMAGE
      else
        record.profile_photo
      end
    }
  }
end
```

### Cover Photo

```ruby
self.cover_photo = {
  size: :md,                         # :sm, :md (default), :lg
  visible_on: [:show, :forms],       # :show, :edit, :new, :index, :forms, :display
  source: -> {
    if view.index?
      DEFAULT_IMAGE
    else
      record.cover_photo
    end
  }
}
```

Source can also be a symbol: `source: :cover_photo` (calls `record.cover_photo`).

---

## Eject Command

Eject Avo's built-in views to customize them. Ejected views must be maintained manually.

### Prepared Partials

```bash
bin/rails generate avo:eject --partial :logo           # app/views/avo/partials/_logo.html.erb
bin/rails generate avo:eject --partial :head            # app/views/avo/partials/_head.html.erb
bin/rails generate avo:eject --partial :header          # app/views/avo/partials/_header.html.erb
bin/rails generate avo:eject --partial :scripts         # app/views/avo/partials/_scripts.html.erb
bin/rails generate avo:eject --partial :sidebar_extra   # app/views/avo/partials/_sidebar_extra.html.erb
bin/rails generate avo:eject --partial :profile_menu_extra
```

### Eject Any Template

```bash
bin/rails generate avo:eject --partial app/views/layouts/avo/application.html.erb
```

### Eject View Components

```bash
bin/rails generate avo:eject --component Avo::Index::TableRowComponent
bin/rails generate avo:eject --component Avo::Views::ResourceIndexComponent --scope admins
```

### Eject Field Components

```bash
bin/rails generate avo:eject --field-components text
bin/rails generate avo:eject --field-components text --view edit
bin/rails generate avo:eject --field-components text --view show --scope admins
```

### Eject Controllers

```bash
bin/rails generate avo:eject --controller application_controller
```

---

## Branding

Customize Avo's appearance via the initializer.

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.branding = {
    colors: {
      background: "248 246 242",
      100 => "#CEE7F8",
      400 => "#399EE5",
      500 => "#0886DE",
      600 => "#066BB2",
    },
    chart_colors: ["#FFB435", "#FFA102", "#CC8102"],
    logo: "/avo-assets/logo.png",
    logomark: "/avo-assets/logomark.png",
    placeholder: "/avo-assets/placeholder.svg",
    favicon: "/avo-assets/favicon.ico"
  }
end
```

### Color Options

| Key | Purpose |
|-----|---------|
| `background` | Page background color (RGB space-separated) |
| `100` | Color hints |
| `400` | Highlights (lighter) |
| `500` | Base primary color |
| `600` | Highlights (darker) |

Color format: hex (`#30A65A`) or RGB (`248 246 242`).

---

## TailwindCSS Integration

Avo uses Tailwind CSS for styling. Access Tailwind utilities in:
- Custom field components
- Custom tool views
- Ejected partials and components
- `PanelComponent` body blocks

Avo provides `helpers.input_classes` for consistent form input styling:

```erb
<%= @form.text_field @field.id,
  class: helpers.input_classes("w-full", has_error: @field.model_errors.include?(@field.id)) %>
```

---

## Panels and Sidebars Layout

### Resource Panels

```ruby
class Avo::Resources::User < Avo::BaseResource
  def fields
    field :id, as: :id, link_to_record: true
    field :email, as: :text

    panel name: "User information", description: "Details" do
      field :first_name, as: :text
      field :last_name, as: :text
    end
  end
end
```

### Main Panel

```ruby
def fields
  main_panel do
    field :id, as: :id
    field :name, as: :text
  end

  field :reviews, as: :has_many

  panel name: "Extra" do
    field :notes, as: :textarea
  end
end
```

### Panel Visibility

```ruby
panel name: "User information", visible: -> { resource.record.enabled? } do
  field :first_name, as: :text
  field :last_name, as: :text
end
```

### Resource Sidebar

```ruby
class Avo::Resources::User < Avo::BaseResource
  def fields
    main_panel do
      field :id, as: :id
      field :first_name, as: :text
      field :last_name, as: :text

      sidebar do
        field :email, as: :gravatar, only_on: :show
        field :active, as: :boolean, only_on: :show
      end
    end
  end
end
```

### Tabs

```ruby
def fields
  field :id, as: :id
  field :email, as: :text

  tabs do
    tab "User information", description: "About this user" do
      panel do
        field :first_name, as: :text
        field :last_name, as: :text
      end
    end

    tab "Activity" do
      field :posts, as: :has_many
      field :comments, as: :has_many
    end
  end
end
```

### Clusters (Horizontal Field Groups)

```ruby
panel "Address" do
  cluster divider: true do
    field :street_address, stacked: true do
      "1234 Elm Street"
    end
    field :city, stacked: true do
      "Los Angeles"
    end
    field :zip_code, stacked: true do
      "15234"
    end
  end
end
```
