---
name: rails-concern
description: Creates Rails concerns for shared behavior across models or controllers with TDD. Use when extracting shared code, creating reusable modules, DRYing up models/controllers, or when user mentions concerns, modules, mixins, or shared behavior.
allowed-tools: Read, Write, Edit, Bash(bin/rails test:*), Glob, Grep
---

# Rails Concern Generator (TDD)

Creates concerns (ActiveSupport::Concern modules) for shared behavior with tests first.

## Quick Start

1. Write failing test testing the concern behavior
2. Run test to confirm RED
3. Implement concern in `app/models/concerns/` or `app/controllers/concerns/`
4. Run test to confirm GREEN

## When to Use Concerns

**Good use cases:**
- Shared validations across multiple models
- Common scopes used by several models
- Shared callbacks (e.g., UUID generation)
- Controller authentication/authorization helpers
- Pagination or filtering logic

**Avoid concerns when:**
- Logic is only used in one place (YAGNI)
- Creating "god" concerns with unrelated methods
- Logic should be a service object instead

## TDD Workflow

### Step 1: Create Concern Test (RED)

For **Model Concerns**, test via a model that includes it:

```ruby
# test/models/concerns/[concern_name]_test.rb
require "test_helper"

class ConcernNameTest < ActiveSupport::TestCase
  setup do
    @test_class = Class.new(ApplicationRecord) do
      self.table_name = "events"
      include ConcernName
    end
    @instance = @test_class.new
  end

  test "adds the expected methods" do
    assert_respond_to @instance, :method_from_concern
  end

  test "#method_from_concern behaves as expected" do
    assert_equal expected_value, @instance.method_from_concern
  end

  test "adds scope" do
    assert_respond_to @test_class, :scope_name
  end
end
```

Alternative: Test through an actual model that uses the concern:

```ruby
# test/models/event_test.rb
require "test_helper"

class EventConcernBehaviorTest < ActiveSupport::TestCase
  test "#method_from_concern does something" do
    event = events(:one)
    assert_equal expected, event.method_from_concern
  end
end
```

For **Controller Concerns**, test via controller tests:

```ruby
# test/controllers/[feature]_controller_test.rb
require "test_helper"

class ResourcesControllerPaginationTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:one)
    sign_in @user
  end

  test "paginates results" do
    get resources_path
    assert_includes response.body, "page"
  end
end
```

### Step 2: Run Test (Confirm RED)

```bash
bin/rails test test/models/concerns/concern_name_test.rb
# OR
bin/rails test test/models/event_test.rb
```

### Step 3: Implement Concern (GREEN)

**Model Concern:**

```ruby
# app/models/concerns/[concern_name].rb
module [ConcernName]
  extend ActiveSupport::Concern

  included do
    # Callbacks
    before_validation :generate_uuid, on: :create

    # Validations
    validates :uuid, presence: true, uniqueness: true

    # Scopes
    scope :with_uuid, ->(uuid) { where(uuid: uuid) }
    scope :recent, -> { order(created_at: :desc) }
  end

  # Class methods
  class_methods do
    def find_by_uuid!(uuid)
      find_by!(uuid: uuid)
    end
  end

  # Instance methods
  def generate_uuid
    self.uuid ||= SecureRandom.uuid
  end

  def short_uuid
    uuid&.split("-")&.first
  end
end
```

**Controller Concern:**

```ruby
# app/controllers/concerns/[concern_name].rb
module [ConcernName]
  extend ActiveSupport::Concern

  included do
    before_action :set_locale
    helper_method :current_locale
  end

  class_methods do
    def skip_locale_for(*actions)
      skip_before_action :set_locale, only: actions
    end
  end

  private

  def set_locale
    I18n.locale = params[:locale] || I18n.default_locale
  end

  def current_locale
    I18n.locale
  end
end
```

### Step 4: Run Test (Confirm GREEN)

```bash
bin/rails test test/models/concerns/concern_name_test.rb
```

## Common Concern Patterns

### Pattern 1: UUID Generation

```ruby
# app/models/concerns/has_uuid.rb
module HasUuid
  extend ActiveSupport::Concern

  included do
    before_validation :generate_uuid, on: :create
    validates :uuid, presence: true, uniqueness: true
  end

  private

  def generate_uuid
    self.uuid ||= SecureRandom.uuid
  end
end
```

### Pattern 2: Soft Delete

```ruby
# app/models/concerns/soft_deletable.rb
module SoftDeletable
  extend ActiveSupport::Concern

  included do
    scope :active, -> { where(deleted_at: nil) }
    scope :deleted, -> { where.not(deleted_at: nil) }

    default_scope { active }
  end

  def soft_delete
    update(deleted_at: Time.current)
  end

  def restore
    update(deleted_at: nil)
  end

  def deleted?
    deleted_at.present?
  end
end
```

### Pattern 3: Searchable

```ruby
# app/models/concerns/searchable.rb
module Searchable
  extend ActiveSupport::Concern

  class_methods do
    def search(query)
      return all if query.blank?

      where("name ILIKE :q OR email ILIKE :q", q: "%#{query}%")
    end
  end
end
```

### Pattern 4: Auditable

```ruby
# app/models/concerns/auditable.rb
module Auditable
  extend ActiveSupport::Concern

  included do
    has_many :audit_logs, as: :auditable, dependent: :destroy

    after_create :log_creation
    after_update :log_update
  end

  private

  def log_creation
    audit_logs.create(action: "created", changes: attributes)
  end

  def log_update
    return unless saved_changes.any?
    audit_logs.create(action: "updated", changes: saved_changes)
  end
end
```

### Pattern 5: Controller Filterable

```ruby
# app/controllers/concerns/filterable.rb
module Filterable
  extend ActiveSupport::Concern

  private

  def apply_filters(scope, allowed_filters)
    allowed_filters.each do |filter|
      if params[filter].present?
        scope = scope.where(filter => params[filter])
      end
    end
    scope
  end
end
```

## Usage

**In Models:**

```ruby
class Event < ApplicationRecord
  include HasUuid
  include SoftDeletable
  include Searchable
end
```

**In Controllers:**

```ruby
class ApplicationController < ActionController::Base
  include Filterable
end
```

## Checklist

- [ ] Test written first (RED)
- [ ] Uses `extend ActiveSupport::Concern`
- [ ] `included` block for callbacks/validations/scopes
- [ ] `class_methods` block for class-level methods
- [ ] Instance methods outside blocks
- [ ] Single responsibility (one purpose per concern)
- [ ] Well-named (describes what it adds)
- [ ] All tests GREEN

## Additional Resources

- [Domain Patterns](reference/domain-patterns.md) — State management, association, behavior, and event tracking concern patterns; controller concerns for scoping, filtering, and timezone; naming conventions, composition, and testing strategies
