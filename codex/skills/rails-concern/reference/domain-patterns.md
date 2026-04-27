# Concern Domain Patterns

## Model Concern Structure

### Pattern 1: State Management Concern

```ruby
# app/models/card/closeable.rb
module Card::Closeable
  extend ActiveSupport::Concern

  included do
    has_one :closure, dependent: :destroy

    scope :open, -> { where.missing(:closure) }
    scope :closed, -> { joins(:closure) }

    after_create_commit :track_card_created_event
  end

  def close(user: Current.user)
    create_closure!(user: user)
    track_event "card_closed", user: user
  end

  def reopen
    closure&.destroy!
    track_event "card_reopened"
  end

  def closed?
    closure.present?
  end

  def open?
    !closed?
  end

  def closed_at
    closure&.created_at
  end

  def closed_by
    closure&.user
  end

  private

  def track_card_created_event
    track_event "card_created" if open?
  end
end
```

### Pattern 2: Association Concern

```ruby
# app/models/card/assignable.rb
module Card::Assignable
  extend ActiveSupport::Concern

  included do
    has_many :assignments, dependent: :destroy
    has_many :assignees, through: :assignments, source: :user

    scope :assigned_to, ->(user) { joins(:assignments).where(assignments: { user: user }) }
    scope :unassigned, -> { where.missing(:assignments) }
  end

  def assign(user)
    assignments.create!(user: user) unless assigned_to?(user)
    track_event "card_assigned", user: user, particulars: { assignee_id: user.id }
  end

  def unassign(user)
    assignments.where(user: user).destroy_all
    track_event "card_unassigned", user: user, particulars: { assignee_id: user.id }
  end

  def assigned_to?(user)
    assignees.include?(user)
  end
end
```

### Pattern 3: Behavior Concern

```ruby
# app/models/card/searchable.rb
module Card::Searchable
  extend ActiveSupport::Concern

  included do
    scope :search, ->(query) { where("title LIKE ? OR body LIKE ?", "%#{query}%", "%#{query}%") }
    scope :with_search_rank, ->(query) {
      select("cards.*")
        .select("CASE
                   WHEN title LIKE ? THEN 3
                   WHEN body LIKE ? THEN 2
                   ELSE 1
                 END as search_rank", "%#{query}%", "%#{query}%")
        .order("search_rank DESC")
    }
  end

  class_methods do
    def search_across_accounts(query)
      search(query).distinct
    end
  end
end
```

### Pattern 4: Event Tracking Concern

```ruby
# app/models/card/eventable.rb
module Card::Eventable
  include ::Eventable

  PERMITTED_ACTIONS = %w[
    card_created card_closed card_reopened
    card_assigned card_unassigned
    card_gilded card_ungilded
    title_changed body_changed
  ]

  def track_title_change(old_title)
    track_event "title_changed", particulars: {
      old_title: old_title,
      new_title: title
    }
  end

  def track_body_change
    track_event "body_changed" if saved_change_to_body?
  end
end
```

## Controller Concern Structure

### Pattern 1: Resource Scoping Concern

```ruby
# app/controllers/concerns/card_scoped.rb
module CardScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_card
    before_action :set_board
  end

  private

  def set_card
    @card = Current.account.cards.find(params[:card_id])
  end

  def set_board
    @board = @card.board
  end

  def render_card_replacement
    respond_to do |format|
      format.turbo_stream do
        render turbo_stream: turbo_stream.replace(
          dom_id(@card, :card_container),
          partial: "cards/container",
          locals: { card: @card.reload }
        )
      end
      format.html { redirect_to @card }
    end
  end
end
```

### Pattern 2: Request Context Concern

```ruby
# app/controllers/concerns/current_request.rb
module CurrentRequest
  extend ActiveSupport::Concern

  included do
    before_action :set_current_request_details
  end

  private

  def set_current_request_details
    Current.user = current_user
    Current.identity = current_identity
    Current.session = current_session
    Current.account = current_account
  end
end
```

### Pattern 3: Filtering Concern

```ruby
# app/controllers/concerns/filter_scoped.rb
module FilterScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_filter
    helper_method :filter, :filtered?
  end

  private

  def set_filter
    @filter = if params[:filter_id].present?
      Current.account.filters.find(params[:filter_id])
    else
      Filter.new(filter_params)
    end
  end

  def filter
    @filter
  end

  def filtered?
    @filter.persisted? || filter_params.any?
  end

  def filter_params
    params.fetch(:filter, {}).permit(:assignee_id, :column_id, :tag_id, :closed)
  end
end
```

### Pattern 4: Timezone Concern

```ruby
# app/controllers/concerns/current_timezone.rb
module CurrentTimezone
  extend ActiveSupport::Concern

  included do
    around_action :set_time_zone
    etag { Current.identity&.timezone }
    helper_method :browser_timezone
  end

  private

  def set_time_zone(&block)
    Time.use_zone(browser_timezone, &block)
  end

  def browser_timezone
    cookies[:timezone].presence || "UTC"
  end
end
```

### Pattern 5: HTTP response caching concern

Extract shared **HTTP caching** (conditional GETs, cache-control) when several controllers repeat the same `fresh_when`, `stale?`, or `expires_in` rules. Low-level fragment or Redis cache usage belongs in the caching skill; this pattern is for **controller-level** response caching only.

```ruby
# app/controllers/concerns/public_index_cache.rb
module PublicIndexCache
  extend ActiveSupport::Concern

  included do
    before_action :set_public_index_cache_headers, only: :index
  end

  private

  def set_public_index_cache_headers
    expires_in 5.minutes, public: true
  end
end
```

```ruby
# app/controllers/concerns/conditional_show_cache.rb
# Include after the before_action that loads the record. Implement http_cache_resource in each controller.
module ConditionalShowCache
  extend ActiveSupport::Concern

  included do
    before_action :maybe_return_not_modified, only: :show
  end

  private

  def maybe_return_not_modified
    fresh_when(http_cache_resource)
  end

  def http_cache_resource
    raise NoMethodError, "Implement #{self.class.name}#http_cache_resource (return the record or etag inputs for fresh_when)"
  end
end
```

```ruby
# In BoardsController
def http_cache_resource
  @board
end
```

## When to Extract a Concern

### Extract when you see:

1. **Repeated associations across models**
   ```ruby
   # Multiple models have:
   has_many :comments, as: :commentable
   has_many :attachments, as: :attachable

   # Extract to:
   # app/models/concerns/commentable.rb
   # app/models/concerns/attachable.rb
   ```

2. **Repeated state patterns**
   ```ruby
   # Multiple models have closure/publication/goldness pattern
   has_one :closure
   def close; end
   def reopen; end
   def closed?; end

   # Extract to Card::Closeable, Board::Publishable, etc.
   ```

3. **Repeated scopes**
   ```ruby
   # Multiple models have:
   scope :recent, -> { order(created_at: :desc) }
   scope :by_creator, ->(user) { where(creator: user) }

   # Extract to Timestampable or Ownable concern
   ```

4. **Repeated controller patterns**
   ```ruby
   # Multiple controllers have:
   before_action :set_parent_resource

   # Extract to ParentScoped concern
   ```

## Concern Naming Conventions

### Model concerns (adjectives):
- `Closeable` - can be closed
- `Publishable` - can be published
- `Watchable` - can be watched
- `Assignable` - can be assigned
- `Searchable` - can be searched
- `Eventable` - tracks events
- `Broadcastable` - broadcasts updates
- `Readable` - can be read/marked as read
- `Colorable` - has color
- `Positionable` - has position

### Controller concerns (nouns or descriptive):
- `CardScoped` - scopes to card
- `BoardScoped` - scopes to board
- `FilterScoped` - handles filtering
- `CurrentRequest` - sets current attributes
- `CurrentTimezone` - handles timezone
- `PublicIndexCache` / `ConditionalShowCache` - shared HTTP cache headers or conditional GET
- `Authentication` - handles auth
- `TurboFlash` - flash via Turbo

## Concern Composition in Models

Models include multiple concerns:

```ruby
# app/models/card.rb
class Card < ApplicationRecord
  include Assignable
  include Attachments
  include Broadcastable
  include Closeable
  include Colored
  include Commentable
  include Entropic
  include Eventable
  include Golden
  include NotNowable
  include Pinnable
  include Positionable
  include Readable
  include Searchable
  include Viewable
  include Watchable

  belongs_to :board
  belongs_to :column

  validates :title, presence: true
end
```

## class_methods Block

```ruby
module Card::Searchable
  extend ActiveSupport::Concern

  included do
    scope :search, ->(query) { where("title LIKE ?", "%#{query}%") }
  end

  class_methods do
    def search_with_ranking(query)
      search(query).order("search_rank DESC")
    end

    def top_results(query, limit: 10)
      search_with_ranking(query).limit(limit)
    end
  end
end
```

## Testing Concerns

### Test the concern in isolation:

```ruby
# test/models/concerns/closeable_test.rb
require "test_helper"

class CloseableTest < ActiveSupport::TestCase
  class DummyCloseable < ApplicationRecord
    self.table_name = "cards"
    include Card::Closeable
  end

  setup do
    @record = DummyCloseable.create!(title: "Test")
  end

  test "close creates closure record" do
    assert_difference -> { Closure.count }, 1 do
      @record.close
    end

    assert @record.closed?
  end

  test "reopen destroys closure record" do
    @record.close

    assert_difference -> { Closure.count }, -1 do
      @record.reopen
    end

    assert @record.open?
  end

  test "closed scope finds closed records" do
    @record.close

    assert_includes DummyCloseable.closed, @record
    refute_includes DummyCloseable.open, @record
  end
end
```

### Test in the context of the model:

```ruby
# test/models/card_test.rb
class CardTest < ActiveSupport::TestCase
  test "closing card tracks event" do
    card = cards(:logo)

    assert_difference -> { card.events.count }, 1 do
      card.close
    end

    assert_equal "card_closed", card.events.last.action
  end
end
```

## Refactoring Workflow

When asked to extract a concern:

1. **Identify the pattern** - Find duplicated code across models/controllers
2. **Name the concern** - Use an adjective describing the capability
3. **Create the file** - `app/models/[model]/[concern].rb` or `app/controllers/concerns/[concern].rb`
4. **Move code** - Associations, validations, scopes, methods
5. **Include it** - Add `include ConcernName` to models/controllers
6. **Write tests** - Test concern in isolation and in context
7. **Remove duplication** - Delete the old code from models/controllers

## Common Concern Patterns Catalog

### State record concerns:
- `Closeable` - has_one :closure, close/reopen methods
- `Publishable` - has_one :publication, publish/unpublish methods
- `Golden` - has_one :goldness, gild/ungild methods
- `NotNowable` - has_one :not_now, postpone/resume methods

### Association concerns:
- `Assignable` - has_many :assignments, assign/unassign methods
- `Watchable` - has_many :watches, watch/unwatch methods
- `Commentable` - has_many :comments, as: :commentable
- `Attachments` - has_many :attachments, as: :attachable

### Behavior concerns:
- `Searchable` - search scopes and methods
- `Positionable` - position attribute and ordering
- `Eventable` - event tracking
- `Broadcastable` - Turbo Stream broadcasting
- `Readable` - read tracking for users
