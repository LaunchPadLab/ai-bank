# Avo Search & Menu Reference

Search configuration with ransack, custom search result display, global search, menu editor with sections/groups/items, sidebar customization, and resource panel/tab layout.

---

## Resource Search

### Setup

Add ransack to your Gemfile:

```ruby
# Gemfile
gem "ransack"
```

### Enable Search on a Resource

```ruby
class Avo::Resources::User < Avo::BaseResource
  self.search = {
    query: -> { query.ransack(name_eq: q).result(distinct: false) }
  }
end
```

The `query` block provides:
- `q` — stripped search query string
- `query` — Active Record relation with authorization scopes applied
- `params[:q]` — unstripped query string

### Ransack v4+ Requirement

```ruby
class User < ApplicationRecord
  def self.ransackable_attributes(auth_object = nil)
    ["name", "email", "first_name", "last_name"]
  end

  def self.ransackable_associations(auth_object = nil)
    ["posts", "comments"]
  end
end
```

### Full Search Example with Multiple Fields

```ruby
class Avo::Resources::User < Avo::BaseResource
  self.search = {
    query: -> {
      query.ransack(
        first_name_cont: q,
        last_name_cont: q,
        email_cont: q,
        m: "or"
      ).result(distinct: false)
    }
  }
end
```

### Custom Search Result Display

```ruby
class Avo::Resources::Post < Avo::BaseResource
  self.search = {
    query: -> { query.ransack(name_cont: q, m: "or").result(distinct: false) },
    item: -> do
      {
        title: "[#{record.id}] #{record.name}",
        description: ActionView::Base.full_sanitizer.sanitize(record.body).truncate(130),
        image_url: main_app.url_for(record.cover_photo),
        image_format: :rounded   # :square, :rounded, or :circle
      }
    end
  }
end
```

### Search Result Options

| Key | Description | License |
|-----|-------------|---------|
| `title` | Main display text | Community |
| `description` | Secondary text below title | Pro+ |
| `image_url` | URL to result image | Pro+ |
| `image_format` | `:square`, `:rounded`, or `:circle` | Pro+ |

### Custom Result Path

```ruby
self.search = {
  query: -> { query.ransack(name_eq: q).result(distinct: false) },
  result_path: -> { avo.resources_city_path(record, custom: "yup") }
}
```

### Help Text in Search Header

```ruby
self.search = {
  query: -> { query.ransack(id_eq: q, m: "or").result(distinct: false) },
  help: -> { "- search by id" }
}
```

### Hide from Global Search

```ruby
self.search = {
  query: -> { query.ransack(id_eq: q, m: "or").result(distinct: false) },
  hide_on_global: true
}
```

### Authorize Search

```ruby
# app/policies/user_policy.rb
class UserPolicy < ApplicationPolicy
  def search?
    true
  end
end
```

Custom authorization method name:

```ruby
Avo.configure do |config|
  config.authorization_methods = {
    search: "avo_search?"
  }
end
```

### Custom Search Provider (e.g., Elasticsearch)

Return an array of hashes instead of Active Record results:

```ruby
class Avo::Resources::Project < Avo::BaseResource
  self.search = {
    query: -> do
      [
        { _id: 1, _label: "Record One", _url: "https://example.com/1" },
        { _id: 2, _label: "Record Two", _url: "https://example.com/2",
          _description: "Some info", _avatar: "https://example.com/avatar.png",
          _avatar_type: :rounded }
      ]
    end
  }
end
```

### Searching Within Associations

```ruby
class Avo::Resources::Application < Avo::BaseResource
  self.search = {
    query: -> {
      query
        .joins(:client)
        .ransack(
          id_eq: q,
          name_cont: q,
          client_first_name_cont: q,
          client_last_name_cont: q,
          client_email_cont: q,
          m: "or"
        ).result(distinct: false)
    }
  }
end
```

### Scope Global vs Resource Search

```ruby
self.search = {
  query: -> {
    if params[:global]
      query.ransack(id_eq: q, m: "or").result(distinct: false)
    else
      query.ransack(id_eq: q, details_cont: q, m: "or").result(distinct: false)
    end
  }
}
```

---

## Global Search

Avo includes global search (CMD+K / Ctrl+K) that searches across all resources with `search` configured.

### Disable Global Search

```ruby
Avo.configure do |config|
  config.disabled_features = [:global_search]
end

# Dynamic (callable)
Avo.configure do |config|
  config.disabled_features = -> { current_user.is_admin? ? [] : [:global_search] }
end
```

### Search Debounce and Result Count

Search debounce and result count display are handled automatically. Result count is not available with custom search providers.

---

## Menu Editor

Customize the sidebar navigation using `main_menu` and `profile_menu` in the initializer.

### Basic Menu Setup

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.main_menu = -> {
    section "Resources", icon: "heroicons/outline/academic-cap" do
      group "Academia" do
        resource :course
        resource :course_link
      end

      group "Blog", collapsable: true, collapsed: true do
        dashboard :dashy
        resource :post
        resource :comment
      end
    end

    section I18n.t("avo.other"), icon: "heroicons/outline/finger-print",
           collapsable: true, collapsed: true do
      link_to "Avo HQ", path: "https://avohq.io", target: :_blank
    end
  }
end
```

### Menu Item Types

| Type | Description |
|------|-------------|
| `link_to` | Custom link with path, target, data attributes |
| `resource` | Auto-generated link to a resource index |
| `dashboard` | Link to a dashboard |
| `section` | Top-level grouping with icon |
| `group` | Sub-grouping within sections |
| `render` | Render a partial or ViewComponent |
| `all_resources` | Auto-list all resources |
| `all_dashboards` | Auto-list all dashboards |
| `all_tools` | Auto-list all custom tools |

### `link_to`

```ruby
link_to "Google", path: "https://google.com", target: :_blank
link_to "Home", main_app.root_path
link_to "Sign out!", main_app.destroy_user_session_path, data: { turbo_method: :delete }
```

### `resource`

```ruby
resource :posts
resource "Avo::Resources::Comments"
resource :posts, label: "News posts"
resource :posts, params: { status: "published" }
resource :users, params: -> do
  { encoded_filters: Avo::Filters::BaseFilter.encode_filters({"Avo::Filters::IsAdmin" => ["non_admins"]}) }
end
```

### `dashboard`

```ruby
dashboard :dashy
dashboard "Sales"
dashboard :dashy, label: "Dashy Dashboard"
```

### `section`

```ruby
section "Resources", icon: "heroicons/outline/academic-cap" do
  resource :course
  resource :course_link
end
```

### `group`

```ruby
group "Blog" do
  resource :posts
  resource :categories
  resource :comments
end
```

### Collapsable Sections and Groups

```ruby
section "Resources", icon: "resources", collapsable: true do
  resource :course
end

section "Resources", icon: "resources", collapsable: true, collapsed: true do
  resource :course
end
```

### `all_` Helpers

```ruby
section "App", icon: "heroicons/outline/beaker" do
  group "Dashboards" do
    all_dashboards
  end

  group "Resources" do
    all_resources except: [:users, :orders]
  end

  group "All tools" do
    all_tools
  end
end
```

### `render`

```ruby
render "avo/sidebar/items/custom_tool"
render "avo/sidebar/items/custom_tool", locals: { something: :here }
render Super::Dooper::Component.new(something: :here)
```

### Icons

Use [Heroicons](https://heroicons.com/) with outline or solid variants:

```ruby
section "Resources", icon: "heroicons/outline/academic-cap" do
  resource :course
end

link_to "Avo", "https://avohq.io", icon: "globe"
```

---

## Menu Item Visibility and Authorization

### Visibility

```ruby
Avo.configure do |config|
  config.main_menu = -> {
    resource :user, visible: -> do
      context[:something] == :something_else
    end
  }
end
```

Available in `visible` block: `current_user`, `context`, `params`, `view_context`.

### Authorization in Menu Items

```ruby
config.main_menu = -> {
  resource :team, visible: -> {
    authorize current_user, Team, "index?", raise_exception: false
  }
}
```

### Data Attributes on Items

```ruby
config.main_menu = -> {
  resource :user, data: { turbo: false }
}
```

---

## Profile Menu

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.profile_menu = -> {
    link_to "Profile", path: "/profile", icon: "user-circle"
  }
end
```

Sign-out link is added automatically. Customize with forms:

```ruby
config.profile_menu = -> {
  link_to "Sign out", path: main_app.destroy_user_session_path,
    icon: "user-circle", method: :post, params: { custom_param: :here }
}
```

### Custom Content in Profile Menu

```bash
bin/rails generate avo:eject --partial :profile_menu_extra
```

---

## Resource Sidebar

Sidebar for compact display of metadata fields within a panel:

```ruby
class Avo::Resources::User < Avo::BaseResource
  def fields
    main_panel do
      field :id, as: :id, link_to_record: true
      field :first_name, as: :text
      field :last_name, as: :text

      tool UserTimeline

      sidebar do
        field :email, as: :gravatar, link_to_record: true, only_on: :show
        field :active, as: :boolean, name: "Is active", only_on: :show
      end
    end
  end
end
```

Disable panel wrapper for custom tools in sidebar:

```ruby
sidebar panel_wrapper: false do
  tool Avo::ResourceTools::SidebarTool
end
```

---

## Panels and Tabs Layout

### Panels

```ruby
def fields
  field :id, as: :id

  panel name: "Details", description: "More information" do
    field :first_name, as: :text
    field :last_name, as: :text
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
end
```

Only fields in root or `main_panel` are visible on the Index view.

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
