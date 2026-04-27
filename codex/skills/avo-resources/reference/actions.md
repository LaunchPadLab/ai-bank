# Avo 3.0 Actions Reference

Comprehensive reference for Avo actions — custom operations on one or multiple records.

---

## Action Structure

Generate an action:

```bash
bin/rails generate avo:action toggle_inactive
bin/rails generate avo:action export_users --standalone
bin/rails generate avo:action admin/approve_user  # namespaced
```

### Basic action

```ruby
# app/avo/actions/toggle_inactive.rb
class Avo::Actions::ToggleInactive < Avo::BaseAction
  self.name = "Toggle Inactive"

  def fields
    field :notify_user, as: :boolean
    field :message, as: :textarea
  end

  def handle(query:, fields:, current_user:, resource:, **args)
    query.each do |record|
      record.update!(inactive: !record.inactive)
      record.notify(fields[:message]) if fields[:notify_user]
    end

    succeed "Successfully toggled status for #{query.count} record(s)"
  end
end
```

---

## The `handle` Method

The core of your action's business logic. Receives:

- **`query`** — selected record(s), single records auto-wrapped in array
- **`fields`** — values from the action's form fields
- **`current_user`** — the authenticated user
- **`resource`** — the Avo resource instance that triggered the action

```ruby
def handle(query:, fields:, current_user:, resource:, **args)
  query.each do |record|
    record.update!(status: fields[:status])
  end

  succeed "Updated #{query.count} records"
end
```

### Accessing arguments

Arguments passed during registration are available via `arguments`:

```ruby
def handle(**args)
  if arguments[:special_message]
    succeed "Custom message!"
  else
    succeed "Default message"
  end
end
```

---

## Fields in Actions

Actions use the same field DSL as resources. Fields appear in the confirmation modal:

```ruby
class Avo::Actions::SendEmail < Avo::BaseAction
  self.name = "Send Email"

  def fields
    field :subject, as: :text, required: true
    field :body, as: :trix
    field :send_copy_to_admin, as: :boolean, default: false
    field :priority, as: :select, options: { High: :high, Normal: :normal, Low: :low }
    field :scheduled_at, as: :date_time
  end

  def handle(query:, fields:, **args)
    query.each do |record|
      EmailService.send(
        to: record.email,
        subject: fields[:subject],
        body: fields[:body],
        priority: fields[:priority]
      )
    end

    succeed "Emails sent to #{query.count} recipients"
  end
end
```

### Conditional fields using arguments

```ruby
class Avo::Actions::City::Update < Avo::BaseAction
  self.name = "Update"
  self.visible = -> { false }

  def fields
    field :name, as: :text if arguments[:render_name]
    field :population, as: :number if arguments[:render_population]
  end

  def handle(fields:, **args)
    City.find(arguments[:cities]).each do |city|
      city.update!(fields)
    end
    succeed "City updated!"
  end
end
```

---

## Feedback Notifications

After an action runs, respond with different notification types. Default is `inform "Action ran successfully"`.

### succeed

Green success alert:

```ruby
succeed "Record updated successfully"
succeed "Task completed", timeout: 5000          # 5-second display
succeed "Important!", timeout: :forever          # stays until dismissed
```

### warn

Orange warning alert:

```ruby
warn "Some records were skipped"
```

### inform

Blue informational alert:

```ruby
inform "Processing started in background"
```

### error

Red error alert:

```ruby
error "Failed to update: #{e.message}"
```

### silent

No notification shown. Useful with redirects:

```ruby
def handle(**args)
  redirect_to "/admin/some-tool"
  silent
end
```

### Multiple notifications

```ruby
def handle(**args)
  succeed "3 records updated"
  warn "2 records skipped"
  error "1 record failed"
end
```

---

## Response Types

Control how the UI responds after the action completes.

### reload (default)

Full page reload:

```ruby
def handle(query:, **args)
  query.each { |r| r.update!(active: false) }
  succeed "Done!"
  reload  # optional — reload is the default
end
```

### redirect_to

Navigate to a different path:

```ruby
def handle(query:, **args)
  query.each { |r| r.update!(active: false) }
  succeed "Done!"
  redirect_to avo.resources_users_path
end

# With options
redirect_to path, allow_other_host: true, status: 303
```

### download

Trigger a file download:

```ruby
class Avo::Actions::DownloadFile < Avo::BaseAction
  self.name = "Download file"

  def handle(query:, **args)
    report_data = []
    query.each { |project| report_data << project.generate_report_data }

    succeed "Done!"
    download report_data, "projects.csv" if report_data.present?
  end
end
```

### keep_modal_open

Keep the modal open (useful for validation errors):

```ruby
class Avo::Actions::CreateUser < Avo::BaseAction
  self.name = "Create User"
  self.standalone = true

  def fields
    field :name, as: :text
    field :birthday, as: :date
  end

  def handle(fields:, **args)
    User.create!(fields)
    succeed "All good!"
  rescue => error
    error "Something happened: #{error.message}"
    keep_modal_open
  end
end
```

### close_modal / do_nothing

Close the modal without page reload. Flashes all notification messages:

```ruby
def handle(**args)
  succeed "Modal closed!"
  close_modal
  # or equivalently:
  # do_nothing
end
```

### navigate_to_action

Redirect to another action. Enables multi-step workflows:

```ruby
class Avo::Actions::City::PreUpdate < Avo::BaseAction
  self.name = "Update"

  def fields
    field :name, as: :boolean
    field :population, as: :boolean
  end

  def handle(query:, fields:, **args)
    navigate_to_action Avo::Actions::City::Update,
      arguments: {
        cities: query.map(&:id),
        render_name: fields[:name],
        render_population: fields[:population]
      }
  end
end
```

### reload_records / reload_record

Refresh specific table rows via Turbo Streams (Index pages only):

```ruby
def handle(query:, fields:, **args)
  query.each { |record| record.update!(active: !record.active) }
  reload_records(query)     # array of records
  # or
  # reload_record(record)   # single record
end
```

### append_to_response

Append custom Turbo Stream responses:

```ruby
def handle(**args)
  succeed "Done!"
  close_modal

  append_to_response -> {
    turbo_stream.set_title("Cool title!")
  }

  # Multiple turbo streams
  append_to_response -> {
    [
      turbo_stream.set_title("Cool title"),
      turbo_stream.replace("sidebar", partial: "shared/sidebar")
    ]
  }
end
```

---

## Standalone Actions

Actions that don't require record selection. Useful for global operations.

```ruby
class Avo::Actions::GlobalReport < Avo::BaseAction
  self.name = "Generate Global Report"
  self.standalone = true

  def fields
    field :date_range, as: :select,
      options: { "Last 7 days": 7, "Last 30 days": 30, "All time": 0 }
  end

  def handle(fields:, current_user:, **args)
    ReportGenerator.new(range: fields[:date_range]).generate
    succeed "Report generated!"
    redirect_to "/admin/reports"
  end
end
```

---

## Action Visibility

Control where actions appear using the `visible` block:

```ruby
class Avo::Actions::PublishPost < Avo::BaseAction
  self.name = "Publish"

  # Boolean
  self.visible = true

  # Block with access to view, resource, parent_resource
  self.visible = -> { view.index? }

  # More complex logic
  self.visible = -> {
    view.show? && resource.record.draft?
  }
end
```

The block executes in `Avo::ExecutionContext` with access to:
- `view` — current view type (index, show, edit)
- `resource` — current resource instance
- `parent_resource` — parent resource (access `parent_resource.record` for the parent record)

---

## Action Authorization

Restrict access using the `authorize` attribute:

```ruby
class Avo::Actions::DestroyData < Avo::BaseAction
  self.authorize = false

  # Or with logic
  self.authorize = -> { current_user.is_admin? }
end
```

Also controlled via Pundit policy `act_on?` method on the resource.

---

## Registering Actions in Resources

### Basic registration

```ruby
class Avo::Resources::User < Avo::BaseResource
  def actions
    action Avo::Actions::ToggleInactive
    action Avo::Actions::SendWelcomeEmail
  end
end
```

### With arguments

```ruby
def actions
  action Avo::Actions::ToggleInactive,
    arguments: { special_message: true }

  # Dynamic arguments
  action Avo::Actions::ToggleInactive,
    arguments: -> do
      { special_message: resource.view.index? && current_user.is_admin? }
    end
end
```

### With icons

```ruby
def actions
  action Avo::Actions::ToggleInactive, icon: "heroicons/outline/globe"
end
```

### With dividers

```ruby
def actions
  action Avo::Actions::ActivateUser
  action Avo::Actions::DeactivateUser

  divider

  action Avo::Actions::SendWelcomeEmail
  action Avo::Actions::SendPasswordReset

  divider label: "Danger Zone"
  action Avo::Actions::DeleteAccount
end
```

---

## Visual Customization

All visual options accept strings or blocks (executed in `Avo::ExecutionContext`):

### Name

```ruby
self.name = "Release fish"
self.name = -> { record.present? ? "Release #{record.name}?" : "Release fish" }
```

### Confirmation message

```ruby
self.message = "Are you sure you want to release the fish?"
self.message = -> {
  if resource.record.present?
    "Are you sure you want to release #{resource.record.name}?"
  else
    "Are you sure you want to release the fish?"
  end
}
```

### Button labels

```ruby
self.confirm_button_label = "Release fish"
self.confirm_button_label = -> { "Release #{resource.record&.name}" }

self.cancel_button_label = "Cancel release"
self.cancel_button_label = -> { "Cancel release on #{resource.record&.name}" }
```

---

## Behavioral Customization

### Skip confirmation modal

```ruby
self.no_confirmation = true
```

### Close modal on backdrop click

```ruby
self.close_modal_on_backdrop_click = false  # prevent closing on backdrop click
```

### Disable Turbo

```ruby
self.turbo = false  # don't use Turbo for this action
```

---

## Customizable Action Controls

Actions can be displayed as standalone buttons outside the dropdown using resource controls:

```ruby
class Avo::Resources::Fish < Avo::BaseResource
  self.show_controls = -> do
    back_button label: "", title: "Go back"
    action Avo::Actions::ReleaseFish, style: :primary, color: :fuchsia, icon: "heroicons/outline/globe"
    actions_list exclude: [Avo::Actions::ReleaseFish], style: :primary, color: :slate
    edit_button label: ""
  end

  self.row_controls = -> do
    action Avo::Actions::ReleaseFish, label: "Release #{record.name}",
      style: :primary, color: :blue, icon: "heroicons/outline/hand-raised"
    edit_button title: "Edit"
    show_button title: "Show"
    delete_button title: "Delete"
    actions_list style: :primary, color: :slate, label: "Actions"
  end

  def actions
    action Avo::Actions::ReleaseFish
  end
end
```

**Action control options:** `title`, `style` (`:primary`, `:outline`, `:text`, `:icon`), `color`, `icon`, `arguments`

---

## Link Arguments Helper

Generate action link paths programmatically:

```ruby
class Avo::Resources::City < Avo::BaseResource
  field :name, as: :text, only_on: :index do
    path, data = Avo::Actions::City::Update.link_arguments(
      resource: resource,
      arguments: {
        cities: Array[resource.record.id],
        render_name: true
      }
    )
    link_to resource.record.name, path, data: data
  end
end

# Without a resource instance
path, data = Avo::Actions::City::Update.link_arguments(
  resource: Avo::Resources::City.new(record: city)
)
link_to "Update city", path, data: data
```

---

## Complete Action Examples

### User activation with notification

```ruby
class Avo::Actions::ActivateUser < Avo::BaseAction
  self.name = "Activate User"
  self.message = -> { "Activate #{query.count} user(s)?" }
  self.confirm_button_label = "Activate"

  def fields
    field :send_welcome_email, as: :boolean, default: true
    field :welcome_message, as: :textarea, default: "Welcome aboard!"
  end

  def handle(query:, fields:, current_user:, **args)
    activated = 0

    query.each do |user|
      user.update!(active: true, activated_by: current_user.id)
      activated += 1

      if fields[:send_welcome_email]
        UserMailer.welcome(user, fields[:welcome_message]).deliver_later
      end
    end

    succeed "Activated #{activated} user(s)"
  end
end
```

### Standalone export action

```ruby
class Avo::Actions::ExportCsv < Avo::BaseAction
  self.name = "Export to CSV"
  self.standalone = true
  self.visible = -> { view.index? }

  def fields
    field :columns, as: :tags,
      suggestions: %w[name email created_at updated_at role],
      enforce_suggestions: true
  end

  def handle(fields:, resource:, **args)
    csv_data = CsvExporter.generate(
      model: resource.model_class,
      columns: fields[:columns]
    )

    download csv_data, "#{resource.model_class.table_name}.csv"
  end
end
```

### Multi-step action flow

```ruby
# Step 1: Select what to update
class Avo::Actions::BulkUpdate::SelectFields < Avo::BaseAction
  self.name = "Bulk Update"

  def fields
    field :update_status, as: :boolean
    field :update_priority, as: :boolean
  end

  def handle(query:, fields:, **args)
    navigate_to_action Avo::Actions::BulkUpdate::ApplyChanges,
      arguments: {
        record_ids: query.map(&:id),
        update_status: fields[:update_status],
        update_priority: fields[:update_priority]
      }
  end
end

# Step 2: Apply the changes
class Avo::Actions::BulkUpdate::ApplyChanges < Avo::BaseAction
  self.name = "Apply Changes"
  self.visible = -> { false }

  def fields
    field :status, as: :select, enum: ::Task.statuses if arguments[:update_status]
    field :priority, as: :select, options: { High: 1, Medium: 2, Low: 3 } if arguments[:update_priority]
  end

  def handle(fields:, **args)
    records = Task.where(id: arguments[:record_ids])
    records.each { |r| r.update!(fields.compact) }
    succeed "Updated #{records.count} records"
  end
end
```

### Resource registration with full controls

```ruby
class Avo::Resources::Post < Avo::BaseResource
  def actions
    action Avo::Actions::PublishPost, icon: "heroicons/outline/eye"
    action Avo::Actions::UnpublishPost, icon: "heroicons/outline/eye-slash"

    divider label: "Export"
    action Avo::Actions::ExportCsv

    divider label: "Danger"
    action Avo::Actions::ArchivePosts
  end
end
```
