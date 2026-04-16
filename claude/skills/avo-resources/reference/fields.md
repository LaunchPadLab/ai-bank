# Avo 3.0 Field Types & Field Options Reference

Comprehensive reference for all Avo field types and configuration options with real code examples.

---

## Declaring Fields

Fields are the backbone of an Avo Resource. Declare them inside the `fields` method:

```ruby
class Avo::Resources::User < Avo::BaseResource
  def fields
    field :id, as: :id
    field :first_name, as: :text
    field :email, as: :text
    field :active, as: :boolean
    field :cv, as: :file
  end
end
```

### View-specific field methods

```ruby
class Avo::Resources::Post < Avo::BaseResource
  def display_fields    # index + show
    field :id, as: :id
    field :title, as: :text
    field :status, as: :badge, options: { success: :published, warning: :draft }
  end

  def form_fields       # new + edit
    field :title, as: :text
    field :body, as: :trix
    field :status, as: :select, options: { Published: :published, Draft: :draft }
  end

  # Also available: index_fields, show_fields, edit_fields, new_fields
end
```

### Conditional fields

The `fields` method has access to `current_user`, `params`, `request`, `view_context`, and `context`:

```ruby
def fields
  field :id, as: :id
  field :name, as: :text

  if current_user.is_admin?
    field :cv, as: :file
  end
end
```

---

## Field Types

### ID

Displays the record's primary key. Visible only on Index and Show views by default.

```ruby
field :id, as: :id
field :id, as: :id, link_to_record: true
```

### Text

Renders an `input[type="text"]` element.

```ruby
field :title, as: :text
field :email, as: :text, protocol: :mailto
field :name, as: :text, link_to_record: true, copyable: true

field :title, as: :text,
  name: "Post title",
  required: true,
  readonly: true,
  as_html: true,
  placeholder: "My shiny new post",
  format_using: -> { value.truncate(30) }
```

**Key options:**
- `as_html: true` — renders value as HTML on Index/Show
- `protocol: :mailto` or `:tel` — wraps value in a protocol link
- `link_to_record: true` — makes the cell a link to the record
- `copyable: true` — adds a clipboard copy icon on hover

### Textarea

Renders a `<textarea>` element. Hidden on Index view by default.

```ruby
field :body, as: :textarea
field :body, as: :textarea, rows: 10
```

**Key options:**
- `rows` — number of visible rows (default: `5`)

### Number

Renders an `input[type="number"]` element.

```ruby
field :age, as: :number
field :age, as: :number, min: 0, max: 120, step: 5
```

**Key options:**
- `min` — minimum allowed value
- `max` — maximum allowed value
- `step` — increment step

### Password

Renders an `input[type="password"]`. Visible only on Edit and New views by default.

```ruby
field :password, as: :password
field :password, as: :password, revealable: true
```

**Key options:**
- `revealable: true` — adds an eye icon to toggle visibility

### Boolean

Renders a checkbox on forms, green check/red X on display views.

```ruby
field :is_published, as: :boolean
field :is_published, as: :boolean, name: "Published", true_value: "yes", false_value: "no"
field :active, as: :boolean, nullable: true  # shows gray icon for nil
field :featured, as: :boolean, as_toggle: true
```

**Key options:**
- `true_value` — what counts as true (default: `[true, "true", "1"]`)
- `false_value` — what counts as false (default: `[false, "false", "0"]`)
- `nullable: true` — renders nil as gray minus-circle icon
- `as_toggle: true` — renders as a toggle switch on forms

### Boolean Group

Updates a Hash with string keys and boolean values. Useful for roles, permissions, feature flags.

```ruby
field :roles, as: :boolean_group,
  name: "User roles",
  options: {
    admin: "Administrator",
    manager: "Manager",
    writer: "Writer"
  }

# Computed options
field :features, as: :boolean_group,
  options: -> do
    record.features.each_with_object({}) do |feature, hash|
      hash[feature.id] = feature.name.humanize
    end
  end
```

**DB payload example:**
```json
{ "admin": true, "manager": true, "writer": false }
```

### Select

Renders a `<select>` dropdown.

```ruby
field :type, as: :select,
  options: { "Large container": :large, "Medium container": :medium, "Tiny container": :tiny },
  display_value: true,
  placeholder: "Choose the type"

# Using enum
field :type, as: :select, enum: ::Project.types, display_value: true

# Computed options
field :type, as: :select,
  options: -> do
    record.get_types_from_the_database.map { |type| [type.name, type.id] }
  end

# Grouped options
field :country, as: :select,
  grouped_options: {
    "North America" => [["United States", "US"], "Canada"],
    "Europe" => ["Denmark", "Germany", "France"]
  }

# Multiple select
field :categories, as: :select, multiple: true

# Include blank
field :type, as: :select, include_blank: "No type"
```

**Key options:**
- `options` — Hash of label => value pairs, or a lambda
- `enum` — use with ActiveRecord enums (alternative to `options`)
- `grouped_options` — creates `<optgroup>` sections
- `display_value: true` — show DB value instead of label on display views
- `include_blank` — `true`, `false`, or a string for the blank option
- `multiple: true` — allow multi-select

### Date

Displays date values with flatpickr date picker on forms.

```ruby
field :birthday, as: :date
field :birthday, as: :date,
  first_day_of_week: 1,
  picker_format: "F J Y",
  format: "yyyy-LL-dd",
  placeholder: "Feb 24th 1955"
```

**Key options:**
- `format` — luxon tokens for Index/Show display
- `picker_format` — flatpickr tokens for Edit/New display
- `picker_options` — hash passed directly to flatpickr
- `first_day_of_week` — 1 (Monday) through 7 (Sunday)
- `disable_mobile: true` — forces flatpickr on mobile devices

### DateTime

Like Date but with time. Supports timezones and 24-hour mode.

```ruby
field :joined_at, as: :date_time,
  name: "Joined at",
  picker_format: "Y-m-d H:i:S",
  format: "yyyy-LL-dd TT",
  time_24hr: true,
  timezone: "PST"

# Relative timezone from record
field :start, as: :date_time, relative: true, timezone: -> { record.timezone }
```

**Key options (in addition to Date options):**
- `time_24hr: true` — 24-hour time picker
- `relative: true` — time is relative to configured timezone
- `timezone` — TZInfo identifier string or lambda

### File

Fastest way to add file uploads via Active Storage.

```ruby
field :avatar, as: :file, is_image: true
field :cover_video, as: :file, accept: "image/*", direct_upload: true
field :document, as: :file, display_filename: false
```

**Key options:**
- `is_image: true` — display as an image
- `accept` — MIME types the input accepts (e.g., `"image/*"`, `"application/pdf"`)
- `direct_upload: true` — upload directly to cloud storage
- `display_filename: false` — hides the filename caption
- `link_to_record: true` — wraps content in a link to the resource

**Authorization:** Requires `upload_{FIELD_ID}?`, `delete_{FIELD_ID}?`, and `download_{FIELD_ID}?` in Pundit policy.

**Variants:**
```ruby
field :photo, as: :file,
  format_using: -> {
    value.variant(resize_to_limit: [150, 150]).processed.image
  }
```

### Files

Upload multiple files at once via Active Storage.

```ruby
field :documents, as: :files
field :photos, as: :files, accept: "image/*", direct_upload: true
```

**Key options (same as File plus):**
- `view_type` — default display: `"grid"` or `"list"`
- `hide_view_type_switcher: true` — hides the grid/list toggle

### Trix

WYSIWYG editor using the Trix editor. Hidden on Index view.

```ruby
field :body, as: :trix
field :body, as: :trix, always_show: true
field :body, as: :trix, attachment_key: :trix_attachments
field :body, as: :trix, attachments_disabled: true
```

**Key options:**
- `always_show: true` — display content directly on Show (default hides under a link)
- `attachment_key` — name of the `has_many_attached` association for file uploads
- `attachments_disabled: true` — hides the paperclip attachment button
- `hide_attachment_filename: true` — hides filename in attachment metadata
- `hide_attachment_filesize: true` — hides filesize in attachment metadata
- `hide_attachment_url: true` — hides URL in attachment metadata

**Active Storage setup:**
```ruby
# Model
class Post < ApplicationRecord
  has_many_attached :trix_attachments
end

# Resource
field :body, as: :trix, attachment_key: :trix_attachments
```

### Markdown (Marksmith)

GitHub-style markdown editor with file uploads and Media Library integration.

```ruby
field :body, as: :markdown
field :body, as: :markdown, media_library: false, file_uploads: false
```

**Requires gems:** `marksmith`, `commonmarker`

**Key options:**
- `media_library: false` — hides the "Attach from gallery" option
- `file_uploads: false` — hides the "Upload files" option
- `extra_preview_params: { foo: :bar }` — passes additional params to preview renderer

### EasyMDE (formerly Markdown)

Renders an EasyMDE Markdown Editor. Hidden on Index view.

```ruby
field :description, as: :easy_mde
field :description, as: :easy_mde, always_show: true, spell_checker: true
```

**Key options:**
- `always_show: true` — display content directly on Show
- `height` — editor height (`"auto"` or pixels)
- `spell_checker: true` — enables spell checking

### Rhino (TipTap-based)

Full WYSIWYG editor based on TipTap. Supports ActiveStorage, ActionText, and Media Library.

```ruby
field :body, as: :rhino
field :body, as: :rhino, always_show: true
```

**Requires gem:** `avo-rhino_field`

### Code

Code editor using CodeMirror. Hidden on Index view.

```ruby
field :custom_css, as: :code, theme: "dracula", language: "css"

field :metadata, as: :code,
  language: "javascript",
  theme: "material-darker",
  height: "250px",
  tab_size: 4,
  indent_with_tabs: false,
  line_wrapping: true

# Auto-format JSON
field :body, as: :code, pretty_generated: true
```

**Key options:**
- `theme` — `"material-darker"` (default), `"eclipse"`, `"dracula"`
- `language` — `"css"`, `"dockerfile"`, `"htmlmixed"`, `"javascript"`, `"markdown"`, `"nginx"`, `"php"`, `"ruby"`, `"sass"`, `"shell"`, `"sql"`, `"vue"`, `"xml"`
- `height` — `"auto"` or pixel value like `"250px"`
- `tab_size` — integer (default: `2`)
- `indent_with_tabs` — boolean (default: `false`)
- `line_wrapping` — boolean (default: `true`)
- `pretty_generated: true` — auto-format and parse JSON

### Key/Value

Edit flat key-value pairs stored as JSON. Hidden on Index view.

```ruby
field :meta, as: :key_value
field :meta, as: :key_value, stacked: true

field :meta, as: :key_value,
  key_label: "Meta key",
  value_label: "Meta value",
  action_text: "New item",
  delete_text: "Remove item",
  disable_editing_keys: false,
  disable_editing_values: false,
  disable_adding_rows: false,
  disable_deleting_rows: false

# Disable all editing
field :meta, as: :key_value, disabled: true
```

**Key options:**
- `key_label` / `value_label` — custom header labels
- `action_text` / `delete_text` — custom button labels
- `disable_editing_keys: true` — prevents key editing (also disables adding rows)
- `disable_editing_values: true` — prevents value editing
- `disable_adding_rows: true` — prevents adding new rows
- `disable_deleting_rows: true` — prevents deleting rows
- `stacked: true` — uses full width layout

### Tags

Add a list of tags to a record. Supports PostgreSQL arrays, `acts-as-taggable-on`, and custom arrays.

```ruby
field :skills, as: :tags

field :skills, as: :tags,
  suggestions: -> { record.skill_suggestions },
  enforce_suggestions: true,
  close_on_select: true,
  suggestions_max_items: 10,
  delimiters: [",", " "]

field :skills, as: :tags,
  disallowed: ["not_allowed", "banned"]

# Single-select mode
field :category, as: :tags, mode: :select

# Fetch values from API
field :skills, as: :tags,
  fetch_values_from: "/avo/resources/skills/skills_for_user"

# With acts-as-taggable-on
field :tags, as: :tags,
  acts_as_taggable_on: :tags,
  close_on_select: false,
  placeholder: "add some tags",
  suggestions: -> { Post.tags_suggestions },
  enforce_suggestions: true
```

**Suggestion objects can include avatars:**
```ruby
def self.tags_suggestions
  [
    { value: 1, label: "one", avatar: "https://example.com/avatar1.jpg" },
    { value: 2, label: "two", avatar: "https://example.com/avatar2.jpg" }
  ]
end
```

**Key options:**
- `suggestions` — array of strings/hashes or lambda
- `enforce_suggestions: true` — only allow values from suggestions
- `suggestions_max_items` — max visible suggestions (default: `20`)
- `close_on_select: true` — close dropdown after selection
- `disallowed` — array of values that cannot be added
- `delimiters` — characters to split input into tags (default: `[","]`)
- `mode: :select` — single value instead of array
- `acts_as_taggable_on` — integration with the gem
- `fetch_values_from` — URL endpoint for dynamic suggestions

### Badge

Displays status with colored badges. Display-only (use Select for editing).

```ruby
field :stage, as: :badge,
  options: {
    info: [:discovery, :idea],
    success: :done,
    warning: "on hold",
    danger: :cancelled,
    neutral: :drafting
  }
```

**Badge types:** `info` (blue), `success` (green), `danger` (red), `warning` (yellow), `neutral` (gray)

**Combined with Select for editing:**
```ruby
field :stage, as: :select,
  hide_on: [:show, :index],
  options: { "Discovery": :discovery, "Done": :done, "Cancelled": :cancelled },
  placeholder: "Choose the stage."

field :stage, as: :badge,
  options: { info: [:discovery], success: :done, danger: :cancelled }
```

### Progress Bar

Renders a `<progress>` element on display views, `input[type=range]` on forms.

```ruby
field :progress, as: :progress_bar
field :progress, as: :progress_bar,
  max: 150,
  step: 10,
  display_value: true,
  value_suffix: "%"
```

**Key options:**
- `max` — maximum value (default: `100`)
- `step` — slider step on forms (default: `1`)
- `display_value: true` — show numeric value above slider
- `value_suffix` — string appended after value (e.g., `"%"`)

### Status

Displays status with loading spinner, success check, or failure X.

```ruby
field :progress, as: :status,
  failed_when: [:closed, :rejected, :failed],
  loading_when: [:loading, :running, :waiting, "in progress"],
  success_when: [:done]
```

**Key options:**
- `failed_when` — array of values for failed state (red)
- `loading_when` — array of values for loading state (spinner)
- `success_when` — array of values for success state (green)
- `neutral_when` — array of values for neutral state (gray)

### Location

Displays a point on a Mapbox map on Show view, coordinate inputs on Edit.

```ruby
field :coordinates, as: :location
field :coordinates, as: :location, stored_as: [:latitude, :longitude]

field :coordinates, as: :location,
  stored_as: [:latitude, :longitude],
  mapkick_options: {
    style: "mapbox://styles/mapbox/satellite-v9",
    controls: true
  }

# Static map image
field :coordinates, as: :location, stored_as: [:latitude, :longitude], static: true
```

**Requires:** `mapkick-rb` gem and `MAPBOX_ACCESS_TOKEN` environment variable.

**Key options:**
- `stored_as: [:latitude, :longitude]` — use separate DB columns
- `mapkick_options` — hash of Mapkick configuration
- `static: true` — render a static map image (requires `mapkick-static` gem)

### Area

Displays a polygon/geometry on a map.

```ruby
field :city_center_area, as: :area,
  geometry: :polygon,
  mapkick_options: {
    style: "mapbox://styles/mapbox/satellite-v9",
    controls: true
  },
  datapoint_options: {
    label: "Paris City Center",
    tooltip: "Bonjour mes amis!",
    color: "#009099"
  }
```

### Money

Displays monetary values with currency selector. Requires `avo-money_field` and `money-rails` gems.

```ruby
field :price, as: :money, currencies: %w[EUR USD RON PEN]
```

**Setup:**
```ruby
# Gemfile
gem "avo-money_field"
gem "money-rails", "~> 1.12"

# Model
class Product < ApplicationRecord
  monetize :price_cents
end
```

**Key options:**
- `currencies` — array of ISO currency codes to show in dropdown

### Preview

Adds a hover preview popup icon on each Index row.

```ruby
field :preview, as: :preview

# Mark fields to show in preview
field :name, as: :text, show_on: :preview
field :description, as: :textarea, show_on: :preview
```

### Heading

Visual separator between field sections. Not tied to any database column.

```ruby
field :user_information, as: :heading
field :some_id, as: :heading, label: "User Information"

# HTML heading
field :dev_heading, as: :heading, as_html: true do
  '<div class="underline uppercase font-bold">DEV</div>'
end
```

**Key options:**
- `label` — custom heading text (renders on all views including forms)
- `as_html: true` — render the heading content as HTML

### External Image

Displays an image from a URL stored in the database.

```ruby
field :logo, as: :external_image
field :logo, as: :external_image,
  width: -> { view.index? ? 40 : 150 },
  height: -> { view.index? ? 40 : 150 },
  radius: -> { view.index? ? 4 : 12 },
  link_to_record: true

# Computed URL
field :logo, as: :external_image do
  "//logo.clearbit.com/#{URI.parse(record.url).host}?size=180"
rescue
  nil
end
```

**Key options:**
- `width` — image width in pixels (default: `40`)
- `height` — image height in pixels (default: `40`)
- `radius` — border radius in pixels (default: `0`)
- `link_to_record: true` — wraps image in a link to the resource

### Gravatar

Turns an email field into a Gravatar avatar image.

```ruby
field :email, as: :gravatar
field :email, as: :gravatar, rounded: false, size: 60, default_url: "https://example.com/default.png"
field :email, as: :gravatar, link_to_record: true

# Computed email
field :email, as: :gravatar do
  "#{record.google_username}@gmail.com"
end
```

**Key options:**
- `rounded: false` — square avatar on Index (default: `true`)
- `size` — avatar size in pixels (default: `32`)
- `default_url` — fallback image URL if email not found in Gravatar

### Hidden

Renders a hidden input on Edit and New views only.

```ruby
field :group_id, as: :hidden
field :user_id, as: :hidden, default: -> { current_user.id }

# Conditional: admin sees belongs_to, others get hidden field
field :user, as: :belongs_to, visible: -> { context[:current_user].admin? }
field :user_id, as: :hidden,
  default: -> { current_user.id },
  visible: -> { !context[:current_user].admin? }
```

### Country

Renders a select with all ISO 3166-1 countries. Requires `countries` gem.

```ruby
field :country, as: :country
field :country, as: :country, display_code: true
```

### Radio

Renders radio buttons for single-value selection.

```ruby
field :role, as: :radio,
  name: "User role",
  options: {
    admin: "Administrator",
    manager: "Manager",
    writer: "Writer"
  }

# Computed options
field :role, as: :radio,
  options: -> do
    record.roles.each_with_object({}) do |role, hash|
      hash[role.id] = role.name.humanize
    end
  end
```

### Stars

Renders star rating with clickable stars on forms.

```ruby
field :rating, as: :stars
field :rating, as: :stars, max: 10
```

**Key options:**
- `max` — maximum number of stars (default: `5`)

### Record Link

Links to another record. Requires the target to have a resource configured.

```ruby
field :post, as: :record_link
field :post, as: :record_link, target: :blank, use_resource: "BigPost"

# Computed value
field :creator, as: :record_link do
  User.find(SomeService.new(comment: record).fetch_user_id)
end
```

**Requires gem:** `avo-record_link_field`

---

## Field Options Reference

### Visibility: show/hide on specific views

```ruby
field :body, as: :text, hide_on: [:index, :show]
field :body, as: :text, show_on: [:edit, :new]
field :body, as: :text, only_on: :forms           # only new + edit
field :body, as: :text, except_on: :forms          # only index + show
field :body, as: :text, only_on: :index
field :body, as: :text, except_on: :display        # only forms

# Available symbols: :new, :edit, :index, :show, :forms, :display, :all
```

### Visible (conditional)

```ruby
field :is_featured, as: :boolean, visible: -> { context[:user].is_admin? }
field :is_featured, as: :boolean, visible: -> { resource.name.include? "user" }
field :is_featured, as: :boolean, visible: -> { resource.record&.published_at.present? }
```

### Sortable

```ruby
field :name, as: :text, sortable: true

# Custom sortable block
field :is_writer, as: :text,
  sortable: -> {
    query.order(id: direction)
  },
  hide_on: :edit do
    record.posts.to_a.size > 0 ? "yes" : "no"
  end

# Sort by association
field :last_commented_at, as: :date,
  sortable: -> {
    query.includes(:comments).order("comments.created_at #{direction}")
  }
```

The custom sortable block receives `query` and `direction`, must return a query.

### Filterable

```ruby
field :name, as: :text, filterable: true
field :created_at, as: :date_time, filterable: true
field :status, as: :select, filterable: true
```

### Computed Fields

Display a value not in the database. Only visible on Index and Show views.

```ruby
field "Has posts", as: :boolean do
  record.posts.present?
rescue
  false
end
```

### Formatting

```ruby
# Format on all views
field :is_writer, as: :text, format_using: -> {
  if view.form?
    value
  else
    value.present? ? "Yes" : "No"
  end
}

# View-specific formatting
field :is_writer, as: :text, format_display_using: -> { value.present? ? "Yes" : "No" }
field :price, as: :number, format_index_using: -> { view_context.number_to_currency(value) }

# Available: format_using, format_display_using, format_index_using,
#            format_show_using, format_edit_using, format_new_using, format_form_using
```

Inside formatting blocks you have access to: `value`, `record`, `resource`, `view`, `field`, `view_context`.

### Update Using (parse before save)

```ruby
field :metadata, as: :code,
  update_using: -> do
    ActiveSupport::JSON.decode(value)
  end
```

### Disabled

Prevents editing AND prevents the value from being submitted (safe from DOM manipulation).

```ruby
field :name, as: :text, disabled: true
field :id, as: :number, disabled: -> { view == :edit }
```

### Readonly

Renders as disabled but the value CAN still be submitted (not safe from DOM manipulation).

```ruby
field :name, as: :text, readonly: true
```

### Required

Adds a visual asterisk. Does NOT add validation — you must add `validates :name, presence: true` on the model.

```ruby
field :name, as: :text, required: true
field :name, as: :text, required: -> { view == :new }
```

### Placeholder

```ruby
field :name, as: :text, placeholder: "John Doe"
```

### Help Text

```ruby
field :custom_css, as: :code, help: "Edit the user's custom styles."
field :password, as: :password, help: 'Verify strength <a href="http://passwordmeter.com/">here</a>.'
```

### Default Value

Sets a default value on the New view.

```ruby
field :name, as: :text, default: "John"
field :level, as: :select,
  options: { "Beginner": :beginner, "Advanced": :advanced },
  default: -> { Time.now.hour < 12 ? "advanced" : "beginner" }
```

### Nullable

Stores `NULL` in the database when the field is empty.

```ruby
field :body, as: :textarea, nullable: true
field :body, as: :textarea, nullable: true, null_values: ["0", "", "null", "nil", nil]
```

### Link to Record

Makes a field value a link to the record's Show page. Works on `id`, `text`, and `gravatar` fields.

```ruby
field :id, as: :id, link_to_record: true
field :name, as: :text, link_to_record: true
```

### Copyable

Adds a clipboard icon to copy the field value.

```ruby
field :name, as: :text, copyable: true
```

### HTML Attributes

Attach `style`, `classes`, and `data` attributes to field wrappers.

```ruby
field :users_required, as: :number,
  html: { index: { wrapper: { classes: "text-right" } } }
```

### Stacked Layout

Uses full horizontal width for the field.

```ruby
field :meta, as: :key_value, stacked: true
```

### Custom Field Name (Label)

```ruby
field :is_available, as: :boolean, name: "Availability"
```

### Summarizable

Adds a visual summary chart in the Index table header for a column.

```ruby
field :status, as: :select, summarizable: true
field :status, as: :badge, summarizable: true
```

### For Attribute

Targets a different model attribute than the field's id.

```ruby
field :status, as: :select, options: [:one, :two, :three], only_on: :forms
field :secondary_field_for_status, as: :badge,
  for_attribute: :status,
  options: { info: :one, success: :two, warning: :three },
  except_on: :forms
```

### Meta

Send arbitrary information to the field, useful for custom fields or custom components.

```ruby
field :status, as: :custom_status, meta: { foo: :bar }
field :status, as: :badge, meta: -> do
  record.statuses.map(&:id)
end
```

### Custom Components

Override the view components used for rendering the field.

```ruby
field :description, as: :text,
  components: {
    index_component: Avo::Fields::Admin::TextField::IndexComponent,
    show_component: Avo::Fields::Admin::TextField::ShowComponent,
    edit_component: "Avo::Fields::Admin::TextField::EditComponent"
  }

# Or as a block
field :description, as: :text,
  components: -> do
    {
      show_component: Avo::Fields::Admin::TextField::ShowComponent,
      edit_component: "Avo::Fields::Admin::TextField::EditComponent"
    }
  end
```

---

## with_options Helper

Apply the same options to multiple fields at once:

```ruby
with_options hide_on: :forms do
  field :name, as: :text, filterable: true
  field :population, as: :number, filterable: true
  field :is_capital, as: :boolean, filterable: true
  field :features, as: :key_value
  field :status, as: :badge, enum: ::City.statuses
end
```

---

## Field Discovery

Auto-detect fields from database columns and model associations:

```ruby
def fields
  discover_columns
  discover_associations
end

# With filtering
def fields
  discover_columns only: [:title, :body, :published_at]
  discover_associations except: [:audit_logs]
end

# Combined with manual fields
def fields
  field :custom_field, as: :text
  discover_columns except: [:custom_field]
  discover_associations
end
```

**Type mapping:** `string` → `:text`, `integer` → `:number`, `boolean` → `:boolean`, `datetime` → `:datetime`, `json/jsonb` → `:code`

**Association mapping:** `belongs_to` → `:belongs_to`, `has_one` → `:has_one`, `has_many` → `:has_many`, `has_one_attached` → `:file`, `has_many_attached` → `:files`, `has_rich_text` → `:trix`

---

## Association Fields

### Belongs To

```ruby
field :user, as: :belongs_to
field :user, as: :belongs_to, searchable: true
field :user, as: :belongs_to, allow_via_detaching: true
field :user, as: :belongs_to, attach_scope: -> { query.non_admins }
field :user, as: :belongs_to, can_create: true

# Polymorphic
field :commentable, as: :belongs_to,
  polymorphic_as: :commentable,
  types: [::Post, ::Project]
```

### Has Many / Has And Belongs To Many

```ruby
field :posts, as: :has_many
field :posts, as: :has_many, searchable: true
```

### Has One

```ruby
field :profile, as: :has_one
```

---

## Complete Resource Example

```ruby
class Avo::Resources::User < Avo::BaseResource
  self.title = :name
  self.includes = [:posts, :profile]
  self.search = {
    query: -> { query.ransack(name_cont: q, email_cont: q, m: "or").result(distinct: false) }
  }

  def fields
    field :id, as: :id, link_to_record: true
    field :email, as: :gravatar, link_to_record: true

    field :heading_personal, as: :heading, label: "Personal Information"
    field :first_name, as: :text, required: true, sortable: true, filterable: true
    field :last_name, as: :text, required: true, sortable: true
    field :email, as: :text, required: true, copyable: true, protocol: :mailto
    field :birthday, as: :date, first_day_of_week: 1

    field :heading_settings, as: :heading, label: "Settings"
    field :active, as: :boolean, sortable: true, filterable: true
    field :role, as: :select, enum: ::User.roles, display_value: true, filterable: true
    field :roles, as: :boolean_group, options: { admin: "Admin", editor: "Editor" }

    field :heading_content, as: :heading, label: "Content"
    field :bio, as: :trix, always_show: true, attachment_key: :bio_attachments
    field :cv, as: :file, is_image: false, visible: -> { current_user.is_admin? }
    field :meta, as: :key_value, stacked: true

    field :posts, as: :has_many
    field :profile, as: :has_one
  end
end
```
