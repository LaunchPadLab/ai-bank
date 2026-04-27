---
name: "viewcomponent-patterns"
description: "Creates ViewComponents for reusable UI elements with TDD. Use when building reusable UI components, extracting complex partials, creating cards/tables/badges/modals, or when user mentions ViewComponent, components, or reusable UI."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools. -->

# ViewComponent Patterns for Rails 8.x

## Overview

ViewComponents are Ruby objects for building reusable, testable view components:
- Faster than partials (no partial lookup)
- Unit testable without full request cycle
- Encapsulate view logic with Ruby
- Type-safe with explicit interfaces

## Quick Start

```bash
# Add to Gemfile
bundle add view_component

# Generate component
bin/rails generate component Card title
```

## TDD Workflow

```
ViewComponent Progress:
- [ ] Step 1: Write component test (RED)
- [ ] Step 2: Run test (fails - no component)
- [ ] Step 3: Generate component skeleton
- [ ] Step 4: Implement component
- [ ] Step 5: Run test (GREEN)
- [ ] Step 6: Add variants/slots if needed
```

## Project Structure

```
app/components/
├── application_component.rb    # Base class
├── card_component.rb
├── card_component.html.erb
├── badge_component.rb
├── badge_component.html.erb
├── table/
│   ├── component.rb
│   ├── component.html.erb
│   ├── header_component.rb
│   └── row_component.rb
└── modal/
    ├── component.rb
    └── component.html.erb

test/components/
├── card_component_test.rb
├── badge_component_test.rb
└── table/
    └── component_test.rb
```

## Step 1: Component Test (RED)

```ruby
# test/components/card_component_test.rb
require "test_helper"

class CardComponentTest < ViewComponent::TestCase
  setup do
    @component = CardComponent.new(title: "Test Title")
  end

  test "renders the title" do
    render_inline(@component)
    assert_selector "h3", text: "Test Title"
  end

  test "renders content block" do
    render_inline(@component) { "Card content" }
    assert_text "Card content"
  end

  test "renders subtitle when provided" do
    component = CardComponent.new(title: "Title", subtitle: "Subtitle")
    render_inline(component)
    assert_selector "p", text: "Subtitle"
  end

  test "does not render subtitle element when not provided" do
    render_inline(@component)
    assert_no_selector ".subtitle"
  end
end
```

## Step 2-4: Implement Component

### Base Component

```ruby
# app/components/application_component.rb
class ApplicationComponent < ViewComponent::Base
  include ActionView::Helpers::TagHelper
  include ActionView::Helpers::NumberHelper

  def not_specified_span
    tag.span(I18n.t("components.common.not_specified"), class: "text-slate-400 italic")
  end
end
```

### Basic Component

```ruby
# app/components/card_component.rb
class CardComponent < ApplicationComponent
  def initialize(title:, subtitle: nil)
    @title = title
    @subtitle = subtitle
  end

  attr_reader :title, :subtitle

  def subtitle?
    subtitle.present?
  end
end
```

```erb
<%# app/components/card_component.html.erb %>
<div class="bg-white rounded-lg shadow p-6">
  <h3 class="text-lg font-semibold text-slate-900"><%= title %></h3>
  <% if subtitle? %>
    <p class="subtitle text-sm text-slate-500"><%= subtitle %></p>
  <% end %>
  <div class="mt-4">
    <%= content %>
  </div>
</div>
```

## Common Patterns

### Pattern 1: Status Badge

```ruby
# app/components/badge_component.rb
class BadgeComponent < ApplicationComponent
  VARIANTS = {
    success: "bg-green-100 text-green-800",
    warning: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
    info: "bg-blue-100 text-blue-800",
    neutral: "bg-slate-100 text-slate-800"
  }.freeze

  def initialize(text:, variant: :neutral)
    @text = text
    @variant = variant.to_sym
  end

  def call
    tag.span(
      @text,
      class: "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium #{variant_classes}"
    )
  end

  private

  def variant_classes
    VARIANTS.fetch(@variant, VARIANTS[:neutral])
  end
end
```

### Pattern 2: Component with Slots

```ruby
# app/components/card_component.rb
class CardComponent < ApplicationComponent
  renders_one :header
  renders_one :footer
  renders_many :actions

  def initialize(title: nil)
    @title = title
  end
end
```

```erb
<%# app/components/card_component.html.erb %>
<div class="bg-white rounded-lg shadow">
  <% if header? %>
    <div class="px-6 py-4 border-b"><%= header %></div>
  <% elsif @title %>
    <div class="px-6 py-4 border-b">
      <h3 class="text-lg font-semibold"><%= @title %></h3>
    </div>
  <% end %>

  <div class="p-6"><%= content %></div>

  <% if footer? || actions? %>
    <div class="px-6 py-4 border-t flex justify-end gap-2">
      <%= footer %>
      <% actions.each do |action| %>
        <%= action %>
      <% end %>
    </div>
  <% end %>
</div>
```

Usage:
```erb
<%= render CardComponent.new do |card| %>
  <% card.with_header do %>
    <h2>Custom Header</h2>
  <% end %>

  <p>Card content here</p>

  <% card.with_action do %>
    <%= link_to "Edit", edit_path, class: "btn" %>
  <% end %>
  <% card.with_action do %>
    <%= link_to "Delete", delete_path, class: "btn-danger" %>
  <% end %>
<% end %>
```

### Pattern 3: Collection Component

```ruby
# app/components/table_component.rb
class TableComponent < ApplicationComponent
  renders_one :header
  renders_many :rows

  def initialize(items: [], columns: [])
    @items = items
    @columns = columns
  end
end
```

```erb
<%# app/components/table_component.html.erb %>
<table class="min-w-full divide-y divide-slate-200">
  <thead class="bg-slate-50">
    <% if header? %>
      <%= header %>
    <% else %>
      <tr>
        <% @columns.each do |column| %>
          <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">
            <%= column[:label] %>
          </th>
        <% end %>
      </tr>
    <% end %>
  </thead>
  <tbody class="bg-white divide-y divide-slate-200">
    <% if rows? %>
      <% rows.each do |row| %>
        <%= row %>
      <% end %>
    <% else %>
      <% @items.each do |item| %>
        <tr>
          <% @columns.each do |column| %>
            <td class="px-6 py-4 whitespace-nowrap">
              <%= item.public_send(column[:key]) %>
            </td>
          <% end %>
        </tr>
      <% end %>
    <% end %>
  </tbody>
</table>
```

### Pattern 4: Modal Component

```ruby
# app/components/modal_component.rb
class ModalComponent < ApplicationComponent
  renders_one :trigger
  renders_one :title
  renders_one :footer

  def initialize(id:, size: :medium)
    @id = id
    @size = size
  end

  def size_classes
    case @size
    when :small then "max-w-md"
    when :medium then "max-w-lg"
    when :large then "max-w-2xl"
    when :full then "max-w-full mx-4"
    end
  end
end
```

### Pattern 5: Wrapping Models (Presenter-like)

```ruby
# app/components/event_card_component.rb
class EventCardComponent < ApplicationComponent
  with_collection_parameter :event

  def initialize(event:)
    @event = event
  end

  delegate :name, :event_date, :status, to: :@event

  def formatted_date
    return not_specified_span if event_date.nil?
    I18n.l(event_date, format: :long)
  end

  def status_badge
    render BadgeComponent.new(text: status.humanize, variant: status_variant)
  end

  private

  def status_variant
    case status.to_sym
    when :confirmed then :success
    when :cancelled then :error
    when :pending then :warning
    else :neutral
    end
  end
end
```

Usage with collection:
```erb
<%= render EventCardComponent.with_collection(@events) %>
```

## Testing Components

### Basic Test Structure

```ruby
class BadgeComponentTest < ViewComponent::TestCase
  test "renders success variant" do
    render_inline(BadgeComponent.new(text: "Active", variant: :success))
    assert_selector ".bg-green-100"
  end

  test "renders error variant" do
    render_inline(BadgeComponent.new(text: "Failed", variant: :error))
    assert_selector ".bg-red-100"
  end

  test "defaults to neutral" do
    render_inline(BadgeComponent.new(text: "Unknown"))
    assert_selector ".bg-slate-100"
  end
end
```

### Testing Slots

```ruby
class CardComponentTest < ViewComponent::TestCase
  test "renders header slot" do
    render_inline(CardComponent.new) do |card|
      card.with_header { "Custom Header" }
    end

    assert_text "Custom Header"
  end

  test "renders multiple action slots" do
    render_inline(CardComponent.new) do |card|
      card.with_action { "Action 1" }
      card.with_action { "Action 2" }
    end

    assert_text "Action 1"
    assert_text "Action 2"
  end
end
```

### Testing Collections

```ruby
class EventCardComponentTest < ViewComponent::TestCase
  test "renders collection" do
    events = 3.times.map { events(:one).dup }
    render_inline(EventCardComponent.with_collection(events))
    assert_selector ".event-card", count: 3
  end
end
```

## Usage in Views

```erb
<%# Simple component %>
<%= render BadgeComponent.new(text: "Active", variant: :success) %>

<%# Component with block %>
<%= render CardComponent.new(title: "Stats") do %>
  <p>Content here</p>
<% end %>

<%# Component with slots %>
<%= render CardComponent.new do |card| %>
  <% card.with_header do %>
    <h2>Header</h2>
  <% end %>
  Content
<% end %>

<%# Collection %>
<%= render EventCardComponent.with_collection(@events) %>
```

## Helpers in Components

```ruby
class PriceComponent < ApplicationComponent
  def initialize(amount_cents:, currency: "EUR")
    @amount_cents = amount_cents
    @currency = currency
  end

  def call
    tag.span(formatted_price, class: "font-mono")
  end

  private

  def formatted_price
    number_to_currency(
      @amount_cents / 100.0,
      unit: @currency,
      format: "%n %u"
    )
  end
end
```

## Previews (Development)

```ruby
# test/components/previews/badge_component_preview.rb
class BadgeComponentPreview < ViewComponent::Preview
  def success
    render BadgeComponent.new(text: "Active", variant: :success)
  end

  def error
    render BadgeComponent.new(text: "Failed", variant: :error)
  end

  def with_long_text
    render BadgeComponent.new(text: "Very long status text here", variant: :info)
  end
end
```

Access at: `http://localhost:3000/rails/view_components`

## Checklist

- [ ] Test written first (RED)
- [ ] Extends `ApplicationComponent`
- [ ] Uses slots for flexible content
- [ ] Variants use constants (Open/Closed)
- [ ] Tested with different inputs
- [ ] Collection rendering tested
- [ ] Preview created for development
- [ ] All tests GREEN

## Reference

- [Domain Patterns](reference/domain-patterns.md) — Design principles, complete component structures, Minitest tests, previews, collections, polymorphic slots, Stimulus integration, i18n, anti-patterns, and checklists

## Agent Verification

- Run focused component tests, for example `bin/rails test test/components/badge_component_test.rb`.
- Open or smoke the component preview when markup, variants, slots, or styling changes.
- Run a caller-level integration/system test when the component behavior depends on surrounding page context.
