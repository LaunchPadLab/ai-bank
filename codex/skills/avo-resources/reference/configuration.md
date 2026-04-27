# Avo Configuration Reference

Complete configuration guide for Avo 3.x: initializer setup, licensing, authentication, authorization, pagination, routing, Turbo, and all `Avo.configure` options.

---

## Initializer Setup

All Avo configuration lives in `config/initializers/avo.rb`:

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.root_path = "/avo"
  config.app_name = "My Admin"
  config.license_key = ENV["AVO_LICENSE_KEY"]
  config.current_user_method = :current_user
end
```

---

## License Key and Tiers

### Setting the License Key

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.license_key = ENV["AVO_LICENSE_KEY"]
end
```

### Gemfile Configuration by Tier

```ruby
# Avo Community (free)
gem "avo", ">= 3.0"

# Avo Pro
gem "avo", ">= 3.0"
gem "avo-pro", ">= 3.0", source: "https://packager.dev/avo-hq/"

# Avo Advanced
gem "avo", ">= 3.0"
gem "avo-advanced", ">= 3.0", source: "https://packager.dev/avo-hq/"
```

### Tier Feature Summary

| Feature | Community | Pro | Advanced |
|---------|:---------:|:---:|:--------:|
| Custom fields, tools | Yes | Yes | Yes |
| Localization | Yes | Yes | Yes |
| Stimulus JS integration | Yes | Yes | Yes |
| Branding | Yes | Yes | Yes |
| Testing helpers | Yes | Yes | Yes |
| Resource cards | — | Yes | Yes |
| Record preview on Index | — | Yes | Yes |
| Dynamic filters | — | — | Yes |
| Custom dynamic filters | — | — | Yes |
| Custom controls | — | — | Yes |
| Resource scopes | — | — | Yes |
| Kanban boards | — | — | Yes |

---

## Root Path

```ruby
Avo.configure do |config|
  config.root_path = "/avo"          # default
  config.root_path = "/admin"        # custom path
end
```

When mounting under a nested scope (`/uk/admin`), set only the last segment:

```ruby
config.root_path = "/admin"          # NOT "/uk/admin"
```

---

## App Name

```ruby
Avo.configure do |config|
  config.app_name = "Avocadelicious"
  # Or dynamic:
  config.app_name = -> { I18n.t("app_name") }
end
```

---

## Current User Method

Tell Avo how to identify the current user:

```ruby
# Devise
config.current_user_method = :current_user

# Custom method name
config.current_user_method = :current_admin

# Block (e.g., from Current attributes)
config.current_user_method do
  Current.user
end
```

---

## Authentication

### `authenticate_with`

Runs as a `before_action` in Avo's `ApplicationController`:

```ruby
Avo.configure do |config|
  config.authenticate_with do
    authenticate_admin_user
  end
end

# Or with explicit session check:
config.authenticate_with do
  redirect_to "/" unless session[:user_id] == 1
end
```

### Devise Integration (Route-Level)

```ruby
# config/routes.rb
authenticate :user, ->(user) { user.admin? } do
  mount_avo at: "/avo"
end
```

---

## User Roles

Avo checks methods on the `current_user` object:

| Role | Method Checked | Helper |
|------|---------------|--------|
| Admin | `is_admin?` | `Avo::Current.user_is_admin?` |
| Developer | `is_developer?` | `Avo::Current.user_is_developer?` |

Developers see detailed backtraces on non-validation errors.

### Customize Role Methods

```ruby
Avo.configure do |config|
  config.is_admin_method = :is_admin?
  config.is_developer_method = :is_developer?
end
```

---

## Sign Out Path

```ruby
# Option 1: Customize the user resource name
config.current_user_resource_name = :current_user
# Generates: destroy_current_user_session_path

# Option 2: Fully custom sign out path
config.sign_out_path_name = :logout_path
```

`sign_out_path_name` takes precedence over `current_user_resource_name`.

---

## Authorization Client

```ruby
# Gemfile
gem "pundit"

# config/initializers/avo.rb
Avo.configure do |config|
  config.authorization_client = :pundit
end
```

Customize authorization method names:

```ruby
config.authorization_methods = {
  index: "index?",
  show: "show?",
  edit: "edit?",
  new: "new?",
  update: "update?",
  create: "create?",
  destroy: "destroy?",
  search: "avo_search?"
}
```

---

## Context

Pass custom data accessible via `Avo::Current.context`:

```ruby
Avo.configure do |config|
  config.set_context do
    {
      foo: "bar",
      params: request.params
    }
  end
end
```

Access: `Avo::Current.context[:foo]`

---

## Cache Store

Avo uses `Rails.cache` by default. Configure caching for the index view:

```ruby
Avo.configure do |config|
  config.cache_resources_on_index_view = true    # default: true
end
```

Disable if you use field `visibility` based on user roles.

---

## Locale and Timezone

```ruby
Avo.configure do |config|
  config.timezone = "UTC"
  config.currency = "USD"
end
```

---

## Pagination

### Per-Page Configuration

```ruby
Avo.configure do |config|
  config.per_page = 24                           # records per page (default: 24)
  config.per_page_steps = [12, 24, 48, 72]       # per-page selector options
  config.via_per_page = 8                        # records in has_many associations
end
```

### Pagination Type

```ruby
config.pagination = {
  type: :countless       # hides total count for performance
}

# Or dynamic:
config.pagination = -> do
  { type: :countless }
end
```

---

## Home Path

```ruby
Avo.configure do |config|
  config.home_path = "/avo/dashboard"

  # Or dynamic:
  config.home_path = -> { avo_dashboards.dashboard_path(:dashy) }
end
```

### Initial Breadcrumbs

```ruby
config.set_initial_breadcrumbs do
  add_breadcrumb "Dashboard", "/avo/dashboard"
end
```

---

## Breadcrumbs

```ruby
config.display_breadcrumbs = true                # default: true
```

Add breadcrumbs in custom tool controllers:

```ruby
class Avo::ToolsController < Avo::ApplicationController
  def custom_tool
    add_breadcrumb "Custom tool"
    @page_title = "Custom Tool"
  end
end
```

---

## Resource Ordering and Display

### ID Links to Resource

```ruby
config.id_links_to_resource = true               # ID fields link to show page
```

### Click Row to View Record

```ruby
config.click_row_to_view_record = true
```

### Resource Controls Placement

```ruby
config.resource_controls_placement = :right      # :left, :right, or :both
```

### Container Width

```ruby
config.full_width_index_view = false             # full-width index only
config.full_width_container = false              # full-width all views
```

### Default View Type

```ruby
config.default_view_type = :table                # :table or :grid
```

### Skip Show View

```ruby
config.skip_show_view = true                     # use edit as default view
```

### First Sorting Option

```ruby
config.first_sorting_option = :desc              # :asc or :desc (default: :desc)
```

---

## Mounting Avo in Routes

### Basic Mount

```ruby
# config/routes.rb
Rails.application.routes.draw do
  mount_avo                          # mounts at config.root_path (default: /avo)
  mount_avo at: "custom_path"       # custom mount point
end
```

### With Authentication

```ruby
authenticate :user, ->(user) { user.admin? } do
  mount_avo
end
```

### Under a Scope

```ruby
scope ":locale" do
  mount_avo
end
```

### Adding Custom Routes to Avo Engine

```ruby
Rails.application.routes.draw do
  mount_avo
end

if defined? ::Avo
  Avo::Engine.routes.draw do
    put "switch_accounts/:id", to: "switch_accounts#update", as: :switch_account

    scope :resources do
      get "courses/cities", to: "courses#cities"
    end
  end
end
```

---

## Turbo Configuration

```ruby
config.turbo = -> do
  { instant_click: true }           # default
end
```

---

## Disable Features

```ruby
config.disabled_features = [:global_search]

# Dynamic:
config.disabled_features = -> { current_user.is_admin? ? [] : [:global_search] }
```

---

## Alert Dismiss Time

```ruby
config.alert_dismiss_time = 5000                 # milliseconds (default: 5000)
```

---

## Logger

```ruby
config.logger = -> {
  file_logger = ActiveSupport::Logger.new(Rails.root.join("log", "avo.log"))
  file_logger.datetime_format = "%Y-%m-%d %H:%M:%S"
  file_logger.formatter = proc do |severity, time, progname, msg|
    "[Avo] #{time}: #{msg}\n"
  end
  file_logger
}
```

---

## Default URL Options (Multitenancy)

```ruby
# config/initializers/avo.rb
config.default_url_options = [:account_id]

# config/routes.rb
scope "/account/:account_id" do
  mount_avo
end
```

---

## Associations Lookup List Limit

```ruby
config.associations_lookup_list_limit = 1000     # default: 1000
```

Use `searchable` on belongs_to fields for unlimited records with better UX.

---

## View Component Path

```ruby
config.view_component_path = "app/frontend/components"   # default: app/components
```

---

## Persistence (UI State)

```ruby
config.persistence = {
  driver: :session           # retains pagination and filter state
}
```

Use Redis or MemCache session store to avoid cookie overflow.

---

## Custom Query Scopes

### Index Query

```ruby
class Avo::Resources::User < Avo::BaseResource
  self.index_query = -> {
    query.order(last_name: :asc)
  }
end
```

### Find Record Method

```ruby
class Avo::Resources::Post < Avo::BaseResource
  self.find_record_method = -> {
    if id.is_a?(Array)
      id.first.to_i == 0 ? query.where(slug: id) : query.where(id: id)
    else
      id.to_i == 0 ? query.find_by_slug(id) : query.find(id)
    end
  }
end
```

### With friendly_id

```ruby
self.find_record_method = -> {
  if id.is_a?(Array)
    query.where(slug: id)
  else
    query.friendly.find(id)
  end
}
```

---

## Full Configuration Example

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.root_path = "/avo"
  config.app_name = -> { I18n.t("app_name") }
  config.license_key = ENV["AVO_LICENSE_KEY"]

  config.current_user_method = :current_user
  config.sign_out_path_name = :destroy_user_session_path
  config.is_admin_method = :is_admin?
  config.is_developer_method = :is_developer?

  config.authenticate_with do
    authenticate_user!
  end

  config.authorization_client = :pundit

  config.set_context do
    {
      params: request.params,
      tenant: Current.account
    }
  end

  config.home_path = "/avo/dashboard"
  config.display_breadcrumbs = true
  config.set_initial_breadcrumbs do
    add_breadcrumb "Dashboard", "/avo/dashboard"
  end

  config.per_page = 24
  config.per_page_steps = [12, 24, 48, 72]
  config.via_per_page = 8

  config.id_links_to_resource = true
  config.default_view_type = :table
  config.cache_resources_on_index_view = true

  config.timezone = "UTC"
  config.currency = "USD"

  config.branding = {
    colors: {
      background: "248 246 242",
      100 => "#CEE7F8",
      400 => "#399EE5",
      500 => "#0886DE",
      600 => "#066BB2"
    },
    logo: "/images/admin-logo.png",
    logomark: "/images/admin-logomark.png",
    favicon: "/images/favicon.ico"
  }

  config.turbo = -> do
    { instant_click: true }
  end

  config.main_menu = -> {
    section "Resources", icon: "heroicons/outline/academic-cap" do
      resource :users
      resource :posts
    end
  }

  config.profile_menu = -> {
    link_to "Profile", path: "/profile", icon: "user-circle"
  }
end
```
