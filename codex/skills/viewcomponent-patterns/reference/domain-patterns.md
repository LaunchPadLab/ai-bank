## ViewComponent Design Principles

### Rails 8 / Turbo 8 Considerations

- **Morphing:** Turbo 8 uses morphing by default - ensure components have stable DOM IDs
- **View Transitions:** Components work seamlessly with view transitions
- **Streams:** Components integrate well with Turbo Streams

### 1. Clear and Predictable API

Each component must have an intuitive interface with well-named parameters:

```ruby
# ✅ GOOD - Clear API with default values
class ButtonComponent < ViewComponent::Base
  def initialize(
    text:,
    variant: :primary,
    size: :medium,
    disabled: false,
    html_attributes: {}
  )
    @text = text
    @variant = variant
    @size = size
    @disabled = disabled
    @html_attributes = html_attributes
  end
end

# ❌ BAD - Too many parameters without structure
class ButtonComponent < ViewComponent::Base
  def initialize(text, color, bg_color, padding, margin, border, radius, disabled)
    # Too complex and difficult to maintain
  end
end
```

### 2. Single Responsibility Principle

Each component must have a single responsibility:

```ruby
# ✅ GOOD - Focused component
class AlertComponent < ViewComponent::Base
  def initialize(message:, type: :info, dismissible: false)
    @message = message
    @type = type
    @dismissible = dismissible
  end
end

# ❌ BAD - Component that does too much
class NotificationComponent < ViewComponent::Base
  def initialize(message:, send_email: false, log_to_db: false)
    # Component should not handle business logic
    send_email_notification if send_email
    log_to_database if log_to_db
  end
end
```

### 3. Use Slots for Composition

Slots allow creating flexible and composable components:

```ruby
# app/components/card_component.rb
class CardComponent < ViewComponent::Base
  renders_one :header
  renders_one :body
  renders_one :footer
  renders_many :actions, "ActionComponent"

  def initialize(variant: :default, **html_attributes)
    @variant = variant
    @html_attributes = html_attributes
  end

  class ActionComponent < ViewComponent::Base
    def initialize(text:, url:, method: :get, **html_attributes)
      @text = text
      @url = url
      @method = method
      @html_attributes = html_attributes
    end
  end
end
```

```erb
<%# app/components/card_component.html.erb %>
<div class="<%= card_classes %>" <%= html_attributes %>>
  <% if header? %>
    <div class="card-header">
      <%= header %>
    </div>
  <% end %>

  <% if body? %>
    <div class="card-body">
      <%= body %>
    </div>
  <% end %>

  <% if actions? %>
    <div class="card-actions">
      <% actions.each do |action| %>
        <%= action %>
      <% end %>
    </div>
  <% end %>

  <% if footer? %>
    <div class="card-footer">
      <%= footer %>
    </div>
  <% end %>
</div>
```

### 4. Conditional Rendering with #render?

Use `#render?` to control component display:

```ruby
class EmptyStateComponent < ViewComponent::Base
  def initialize(collection:, message: "No items found")
    @collection = collection
    @message = message
  end

  def render?
    @collection.empty?
  end
end
```

### 5. Variants for Multiple Contexts

Use variants to adapt components according to context:

```ruby
class NavigationComponent < ViewComponent::Base
  def initialize(user:)
    @user = user
  end

  # Default template: app/components/navigation_component.html.erb
  # Mobile template: app/components/navigation_component.html+phone.erb
  # Tablet template: app/components/navigation_component.html+tablet.erb
end
```

## Complete Component Structure

### Component with All Elements

```ruby
# app/components/profile_card_component.rb
class ProfileCardComponent < ViewComponent::Base
  # Slots for composition
  renders_one :avatar
  renders_one :badge
  renders_many :actions, ->(text:, url:, **options) do
    link_to text, url, class: action_classes, **options
  end

  # Configuration
  strip_trailing_whitespace

  def initialize(profile:, variant: :default, show_details: false, **html_attributes)
    @profile = profile
    @variant = variant
    @show_details = show_details
    @html_attributes = html_attributes
  end

  # Hook before rendering
  def before_render
    @formatted_name = @profile.full_name.titleize
  end

  # Conditional rendering
  def render?
    @profile.present? && @profile.active?
  end

  private

  def card_classes
    base = "profile-card"
    variants = {
      default: "profile-card--default",
      compact: "profile-card--compact",
      detailed: "profile-card--detailed"
    }

    "#{base} #{variants[@variant]}"
  end

  def action_classes
    "profile-card__action"
  end

  def html_attributes
    default_attrs = { data: { controller: "profile-card" } }
    default_attrs.merge(@html_attributes)
      .map { |k, v| "#{k}='#{v}'" }
      .join(" ")
      .html_safe
  end
end
```

```erb
<%# app/components/profile_card_component.html.erb %>
<div class="<%= card_classes %>" <%= html_attributes %>>
  <div class="profile-card__header">
    <% if avatar? %>
      <%= avatar %>
    <% else %>
      <div class="profile-card__avatar-placeholder">
        <%= @profile.initials %>
      </div>
    <% end %>

    <div class="profile-card__info">
      <h3 class="profile-card__name"><%= @formatted_name %></h3>
      <% if @show_details %>
        <p class="profile-card__details"><%= @profile.email %></p>
      <% end %>
    </div>

    <% if badge? %>
      <div class="profile-card__badge">
        <%= badge %>
      </div>
    <% end %>
  </div>

  <% if actions? %>
    <div class="profile-card__actions">
      <% actions.each do |action| %>
        <%= action %>
      <% end %>
    </div>
  <% end %>
</div>
```

## Complete Minitest Tests

### Recommended Test Structure

```ruby
# test/components/profile_card_component_test.rb
require "test_helper"

class ProfileCardComponentTest < ViewComponent::TestCase
  setup do
    @profile = Profile.new(first_name: "Jane", last_name: "Doe", email: "jane@example.com", active: true)
  end

  test "renders the profile name" do
    render_inline(ProfileCardComponent.new(profile: @profile))

    assert_css ".profile-card__name", text: "Jane Doe"
  end

  test "does not show details by default" do
    render_inline(ProfileCardComponent.new(profile: @profile))

    assert_no_css ".profile-card__details"
  end

  test "renders default variant classes" do
    render_inline(ProfileCardComponent.new(profile: @profile))

    assert_css ".profile-card.profile-card--default"
  end

  test "displays profile details when show_details is true" do
    render_inline(ProfileCardComponent.new(profile: @profile, show_details: true))

    assert_css ".profile-card__details", text: "jane@example.com"
  end

  test "applies compact variant classes" do
    render_inline(ProfileCardComponent.new(profile: @profile, variant: :compact))

    assert_css ".profile-card.profile-card--compact"
  end

  test "merges custom HTML attributes" do
    render_inline(ProfileCardComponent.new(
      profile: @profile,
      id: "custom-id",
      data: { action: "click->modal#open" }
    ))

    assert_css "#custom-id[data-action='click->modal#open']"
  end

  test "renders custom avatar content" do
    render_inline(ProfileCardComponent.new(profile: @profile)) do |component|
      component.with_avatar do
        "<img src='/avatar.jpg' alt='Avatar'>".html_safe
      end
    end

    assert_css "img[src='/avatar.jpg']"
  end

  test "renders placeholder with initials without avatar slot" do
    render_inline(ProfileCardComponent.new(profile: @profile))

    assert_css ".profile-card__avatar-placeholder", text: @profile.initials
  end

  test "renders the badge slot" do
    render_inline(ProfileCardComponent.new(profile: @profile)) do |component|
      component.with_badge do
        "<span class='badge'>Premium</span>".html_safe
      end
    end

    assert_css ".profile-card__badge .badge", text: "Premium"
  end

  test "renders multiple actions" do
    render_inline(ProfileCardComponent.new(profile: @profile)) do |component|
      component.with_action(text: "Edit", url: "/profiles/1/edit")
      component.with_action(text: "Delete", url: "/profiles/1", method: :delete)
    end

    assert_link "Edit", href: "/profiles/1/edit"
    assert_link "Delete", href: "/profiles/1"
  end

  test "does not render actions section without actions slot" do
    render_inline(ProfileCardComponent.new(profile: @profile))

    assert_no_css ".profile-card__actions"
  end

  test "renders component when profile is active" do
    render_inline(ProfileCardComponent.new(profile: @profile))

    assert_css ".profile-card"
  end

  test "does not render component when profile is inactive" do
    inactive_profile = Profile.new(active: false)
    render_inline(ProfileCardComponent.new(profile: inactive_profile))

    assert_no_css ".profile-card"
  end

  test "does not render component when profile is nil" do
    render_inline(ProfileCardComponent.new(profile: nil))

    assert_no_css ".profile-card"
  end

  test "returns correct classes for variant" do
    component = ProfileCardComponent.new(profile: @profile, variant: :compact)
    assert_equal "profile-card profile-card--compact", component.send(:card_classes)
  end
end
```

## Previews for Documentation

```ruby
# test/components/previews/profile_card_component_preview.rb
class ProfileCardComponentPreview < ViewComponent::Preview
  # Default preview
  # @label Default
  def default
    profile = Profile.new(
      first_name: "Jane",
      last_name: "Doe",
      email: "jane@example.com",
      active: true
    )

    render(ProfileCardComponent.new(profile: profile))
  end

  # Compact variant
  # @label Compact
  def compact
    profile = Profile.new(first_name: "John", last_name: "Smith", active: true)
    render(ProfileCardComponent.new(profile: profile, variant: :compact))
  end

  # With details visible
  # @label With Details
  def with_details
    profile = Profile.new(
      first_name: "Alice",
      last_name: "Johnson",
      email: "alice@example.com",
      active: true
    )

    render(ProfileCardComponent.new(profile: profile, show_details: true))
  end

  # With custom avatar
  # @label With Custom Avatar
  def with_avatar
    profile = Profile.new(first_name: "Bob", last_name: "Wilson", active: true)

    render(ProfileCardComponent.new(profile: profile)) do |component|
      component.with_avatar do
        tag.img(src: "https://i.pravatar.cc/150?img=3", alt: "Avatar", class: "rounded-full w-12 h-12")
      end
    end
  end

  # With badge and actions
  # @label Complete Card
  def with_all_slots
    profile = Profile.new(
      first_name: "Sarah",
      last_name: "Connor",
      email: "sarah@example.com",
      active: true
    )

    render(ProfileCardComponent.new(profile: profile, show_details: true)) do |component|
      component.with_avatar do
        tag.img(src: "https://i.pravatar.cc/150?img=5", alt: "Avatar", class: "rounded-full w-12 h-12")
      end

      component.with_badge do
        tag.span("Premium", class: "badge badge-primary")
      end

      component.with_action(text: "View Profile", url: "#")
      component.with_action(text: "Send Message", url: "#")
    end
  end

  # Dynamic parameters from URL
  # @label Dynamic
  def dynamic(first_name: "Dynamic", last_name: "Profile", show_details: false)
    profile = Profile.new(
      first_name: first_name,
      last_name: last_name,
      email: "#{first_name.downcase}@example.com",
      active: true
    )

    render(ProfileCardComponent.new(profile: profile, show_details: show_details))
  end

  # With template
  def with_template
    render_with_template(locals: {
      profiles: [
        Profile.new(first_name: "Profile", last_name: "One", active: true),
        Profile.new(first_name: "Profile", last_name: "Two", active: true),
        Profile.new(first_name: "Profile", last_name: "Three", active: true)
      ]
    })
  end
end
```

```erb
<%# test/components/previews/profile_card_component_preview/with_template.html.erb %>
<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
  <% profiles.each do |profile| %>
    <%= render(ProfileCardComponent.new(profile: profile, show_details: true)) %>
  <% end %>
</div>
```

## Collections with ViewComponent

### Collection Rendering

```ruby
# app/components/item_card_component.rb
class ItemCardComponent < ViewComponent::Base
  with_collection_parameter :item

  def initialize(item:, item_counter: nil, item_iteration: nil)
    @item = item
    @counter = item_counter
    @iteration = item_iteration
  end

  def featured?
    @iteration&.first?
  end

  def card_classes
    classes = ["item-card"]
    classes << "item-card--featured" if featured?
    classes.join(" ")
  end
end
```

```erb
<%# app/views/items/index.html.erb %>
<div class="items-grid">
  <%= render(ItemCardComponent.with_collection(@items)) %>
</div>
```

### Collection Test

```ruby
# test/components/item_card_component_test.rb
require "test_helper"

class ItemCardComponentTest < ViewComponent::TestCase
  test "renders all items in collection" do
    items = [items(:one), items(:two), items(:three)]
    render_inline(ItemCardComponent.with_collection(items))

    assert_css ".item-card", count: 3
  end

  test "marks first item as featured" do
    items = [items(:one), items(:two), items(:three)]
    render_inline(ItemCardComponent.with_collection(items))

    assert_css ".item-card--featured", count: 1
  end
end
```

## Polymorphic Components with Slots

```ruby
# app/components/list_item_component.rb
class ListItemComponent < ViewComponent::Base
  renders_one :visual, types: {
    icon: IconComponent,
    avatar: ->(src:, alt:, **options) do
      AvatarComponent.new(src: src, alt: alt, size: :small, **options)
    end,
    image: ImageComponent
  }

  renders_one :content
  renders_many :actions, "ActionComponent"

  def initialize(title:, **html_attributes)
    @title = title
    @html_attributes = html_attributes
  end

  class ActionComponent < ViewComponent::Base
    def initialize(label:, url:, **html_attributes)
      @label = label
      @url = url
      @html_attributes = html_attributes
    end
  end
end
```

```erb
<%# Usage %>
<%= render(ListItemComponent.new(title: "John Doe")) do |item| %>
  <% item.with_visual_avatar(src: "/avatar.jpg", alt: "John") %>
  <% item.with_content do %>
    <p>Software Engineer</p>
  <% end %>
  <% item.with_action(label: "View", url: "#") %>
  <% item.with_action(label: "Edit", url: "#") %>
<% end %>
```

## Stimulus Integration

```ruby
# app/components/dropdown_component.rb
class DropdownComponent < ViewComponent::Base
  renders_one :trigger
  renders_many :items, "ItemComponent"

  def initialize(position: :bottom, **html_attributes)
    @position = position
    @html_attributes = html_attributes
  end

  def dropdown_data
    {
      controller: "dropdown",
      dropdown_position_value: @position,
      action: "click@window->dropdown#close"
    }
  end

  class ItemComponent < ViewComponent::Base
    def initialize(text:, url: nil, method: :get, **html_attributes)
      @text = text
      @url = url
      @method = method
      @html_attributes = html_attributes
    end
  end
end
```

```erb
<%# app/components/dropdown_component.html.erb %>
<div data-<%= dropdown_data.map { |k, v| "#{k}='#{v}'" }.join(" ") %> class="dropdown">
  <div data-action="click->dropdown#toggle">
    <%= trigger %>
  </div>

  <div data-dropdown-target="menu" class="dropdown-menu hidden">
    <% items.each do |item| %>
      <%= item %>
    <% end %>
  </div>
</div>
```

## i18n Translations

```ruby
# app/components/notification_component.rb
class NotificationComponent < ViewComponent::Base
  def initialize(type: :info)
    @type = type
  end

  def title
    t(".title.#{@type}")
  end

  def icon
    t(".icon.#{@type}")
  end
end
```

```yaml
# app/components/notification_component.yml
en:
  title:
    info: "Information"
    warning: "Warning"
    error: "Error"
    success: "Success"
  icon:
    info: "ℹ️"
    warning: "⚠️"
    error: "❌"
    success: "✅"

fr:
  title:
    info: "Information"
    warning: "Attention"
    error: "Erreur"
    success: "Succès"
  icon:
    info: "ℹ️"
    warning: "⚠️"
    error: "❌"
    success: "✅"
```

## Component Creation Workflow

### Step 1: Analyze Requirements

Before creating a component, ask yourself these questions:
- What is the single responsibility of the component?
- Which parameters are required vs optional?
- Does the component need slots for flexibility?
- What variants or states should the component support?
- Are JavaScript interactions necessary?

### Step 2: Generate Component

```bash
bin/rails generate view_component:component Alert type message dismissible --sidecar --preview
```

### Step 3: Implement Component

1. Define initializer with clear API
2. Add slots if necessary
3. Implement private helper methods
4. Add `#render?` if necessary
5. Create template

### Step 4: Write Tests

1. Rendering tests with minimal parameters
2. Tests for each variant/option
3. Tests for each slot (present and absent)
4. Tests for `#render?` if applicable
5. Integration tests with Rails helpers

### Step 5: Create Lookbook Previews

1. Default preview
2. Preview for each variant
3. Preview with all slots filled
4. Preview with dynamic parameters
5. Add descriptive notes and scenarios to Lookbook

### Step 6: Validate

```bash
# Run tests
bin/rails test test/components/alert_component_test.rb

# Check linting
bundle exec rubocop -a app/components/alert_component.rb

# Visually check Lookbook previews
# Visit /lookbook to view and verify component in all scenarios
```

## Anti-Patterns to Avoid

### ❌ Business Logic in Components

```ruby
# BAD
class OrderComponent < ViewComponent::Base
  def initialize(order:)
    @order = order
    # Do NOT do business calculations here
    @total = calculate_total_with_tax_and_discount
    @order.update!(processed: true) # NEVER side effects!
  end
end
```

```ruby
# GOOD
class OrderComponent < ViewComponent::Base
  def initialize(order:, total:)
    @order = order
    @total = total # Receives already calculated data
  end
end
```

### ❌ Overly Generic Components

```ruby
# BAD - Too abstract
class GenericComponent < ViewComponent::Base
  def initialize(type:, data:, options: {})
    # Too flexible = difficult to maintain
  end
end
```

```ruby
# GOOD - Specific and clear
class ProfileHeaderComponent < ViewComponent::Base
  def initialize(profile:, show_actions: false)
    @profile = profile
    @show_actions = show_actions
  end
end
```

### ❌ Hidden Dependencies

```ruby
# BAD - Depends on global variables
class NavigationComponent < ViewComponent::Base
  def initialize
    @user = Current.user # Hidden coupling
  end
end
```

```ruby
# GOOD - Explicit dependencies
class NavigationComponent < ViewComponent::Base
  def initialize(user:)
    @user = user
  end
end
```

## Checklist Before Submitting a Component

✅ **Code:**
- [ ] Component has single clear responsibility
- [ ] Required parameters are explicit
- [ ] Default values are sensible
- [ ] Private methods are truly private
- [ ] Component uses `strip_trailing_whitespace` if necessary

✅ **Tests:**
- [ ] Rendering tests with minimal parameters
- [ ] Tests for all variants/options
- [ ] Tests for all slots (present and absent)
- [ ] Tests for `#render?` if applicable
- [ ] Coverage ≥ 95%

✅ **Documentation:**
- [ ] Lookbook preview created with default scenario
- [ ] Lookbook previews for main variants
- [ ] Descriptive notes added to Lookbook scenarios
- [ ] Comments for public methods if necessary
- [ ] i18n file created if necessary

✅ **Quality:**
- [ ] RuboCop passes without errors
- [ ] No potential N+1 queries
- [ ] Accessibility verified (ARIA labels, etc.)
- [ ] Responsive design tested

## Resources and Help

- **Official documentation:** https://viewcomponent.org/
- **Lookbook documentation:** https://lookbook.build/
- **Lookbook previews:** Visit `/lookbook` in development to view component gallery
- **Tests:** `bin/rails test test/components/ -v`
- **Project examples:** Check existing components in `app/components/`
