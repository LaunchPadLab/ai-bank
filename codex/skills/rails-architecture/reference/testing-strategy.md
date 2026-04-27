# Testing Strategy by Layer

## Test Pyramid

```
        /\
       /  \  System Tests (few)
      /----\
     /      \  Integration Tests (moderate)
    /--------\
   /          \  Unit Tests (many)
  --------------
  Models, Services, Queries, Presenters
```

## Unit Tests

### Model Tests

Test validations, scopes, and instance methods:

```ruby
# test/models/event_test.rb
require "test_helper"

class EventTest < ActiveSupport::TestCase
  test "validates presence of name" do
    event = Event.new(event_date: 1.week.from_now, account: accounts(:one))
    assert_not event.valid?
    assert event.errors.added?(:name, :blank)
  end

  test "validates presence of event_date" do
    event = Event.new(name: "Test", account: accounts(:one))
    assert_not event.valid?
    assert event.errors.added?(:event_date, :blank)
  end

  test "belongs to account" do
    event = events(:one)
    assert_respond_to event, :account
    assert_instance_of Account, event.account
  end

  test "has many vendors through event_vendors" do
    event = events(:one)
    assert_respond_to event, :vendors
  end

  test ".upcoming returns only future events" do
    past_event = events(:past)
    future_event = events(:upcoming)

    result = Event.upcoming
    assert_includes result, future_event
    assert_not_includes result, past_event
  end

  test "#days_until returns days until event" do
    event = Event.new(event_date: 5.days.from_now.to_date)
    assert_equal 5, event.days_until
  end
end
```

### Service Tests

Test business logic and error handling:

```ruby
# test/services/orders/create_service_test.rb
require "test_helper"

class Orders::CreateServiceTest < ActiveSupport::TestCase
  setup do
    @service = Orders::CreateService.new
    @user = users(:one)
    @product = products(:widget)
  end

  test "returns success with valid params" do
    params = { user: @user, items: [{ product_id: @product.id, quantity: 2 }] }
    result = @service.call(**params)
    assert result.success?
  end

  test "creates an order with valid params" do
    params = { user: @user, items: [{ product_id: @product.id, quantity: 2 }] }
    assert_difference "Order.count", 1 do
      @service.call(**params)
    end
  end

  test "returns the order on success" do
    params = { user: @user, items: [{ product_id: @product.id, quantity: 2 }] }
    result = @service.call(**params)
    assert_instance_of Order, result.data
  end

  test "returns failure with empty items" do
    params = { user: @user, items: [] }
    result = @service.call(**params)
    assert result.failure?
    assert_equal :empty_cart, result.code
  end

  test "does not create order with empty items" do
    params = { user: @user, items: [] }
    assert_no_difference "Order.count" do
      @service.call(**params)
    end
  end

  test "returns failure with insufficient inventory" do
    params = { user: @user, items: [{ product_id: @product.id, quantity: 100 }] }
    result = @service.call(**params)
    assert result.failure?
    assert_equal :out_of_stock, result.code
  end
end
```

### Query Tests

Test query results and tenant isolation:

```ruby
# test/queries/active_events_query_test.rb
require "test_helper"

class ActiveEventsQueryTest < ActiveSupport::TestCase
  setup do
    @account = accounts(:one)
    @other_account = accounts(:two)
    @active_event = events(:active)
    @inactive_event = events(:cancelled)
    @other_event = events(:other_account_active)
  end

  test "returns active events for account" do
    query = ActiveEventsQuery.new(account: @account)
    assert_includes query.call, @active_event
  end

  test "excludes inactive events" do
    query = ActiveEventsQuery.new(account: @account)
    assert_not_includes query.call, @inactive_event
  end

  test "excludes other account events (tenant isolation)" do
    query = ActiveEventsQuery.new(account: @account)
    assert_not_includes query.call, @other_event
  end
end
```

### Presenter Tests

Test formatting and HTML output:

```ruby
# test/presenters/event_presenter_test.rb
require "test_helper"

class EventPresenterTest < ActiveSupport::TestCase
  setup do
    @event = events(:confirmed)
    @presenter = EventPresenter.new(@event)
  end

  test "delegates to model" do
    assert_equal @event.name, @presenter.name
  end

  test "status_badge returns HTML-safe string" do
    assert_predicate @presenter.status_badge, :html_safe?
  end

  test "status_badge includes status text" do
    assert_includes @presenter.status_badge, "Confirmed"
  end

  test "status_badge uses correct color for confirmed" do
    assert_includes @presenter.status_badge, "bg-green"
  end

  test "formatted_date formats date when present" do
    assert_includes @presenter.formatted_date, @event.event_date.year.to_s
  end

  test "formatted_date returns placeholder when date nil" do
    @event.update_columns(event_date: nil)
    presenter = EventPresenter.new(@event.reload)
    assert_includes presenter.formatted_date, "text-slate-400"
  end
end
```

## Integration Tests

### Request Tests

Test HTTP flow and response:

```ruby
# test/integration/events_test.rb
require "test_helper"

class EventsTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:one)
    @account = @user.account
    @event = events(:one)
    sign_in @user
  end

  test "GET /events returns success" do
    get events_path
    assert_response :ok
  end

  test "GET /events shows user's events" do
    get events_path
    assert_includes response.body, @event.name
  end

  test "GET /events does not show other accounts' events" do
    other_event = events(:other_account)
    get events_path
    assert_not_includes response.body, other_event.name
  end

  test "POST /events creates event" do
    valid_params = { event: { name: "New Event", event_date: 1.week.from_now } }
    assert_difference "Event.count", 1 do
      post events_path, params: valid_params
    end
  end

  test "POST /events redirects to event" do
    valid_params = { event: { name: "New Event", event_date: 1.week.from_now } }
    post events_path, params: valid_params
    assert_redirected_to Event.last
  end

  test "POST /events renders form with errors for invalid params" do
    invalid_params = { event: { name: "" } }
    post events_path, params: invalid_params
    assert_response :unprocessable_entity
  end
end
```

### Policy Tests

Test authorization rules:

```ruby
# test/policies/event_policy_test.rb
require "test_helper"

class EventPolicyTest < ActiveSupport::TestCase
  setup do
    @account = accounts(:one)
    @event = events(:one)
  end

  test "owner can show, edit, update, and destroy" do
    user = users(:one)
    policy = EventPolicy.new(user, @event)

    assert policy.show?
    assert policy.edit?
    assert policy.update?
    assert policy.destroy?
  end

  test "user from different account is forbidden" do
    other_user = users(:other_account)
    policy = EventPolicy.new(other_user, @event)

    assert_not policy.show?
    assert_not policy.edit?
    assert_not policy.update?
    assert_not policy.destroy?
  end

  test "scope returns only own events" do
    user = users(:one)
    scope = EventPolicy::Scope.new(user, Event).resolve

    assert_includes scope, @event
    assert_not_includes scope, events(:other_account)
  end
end
```

## System Tests

Test critical user journeys:

```ruby
# test/system/create_event_test.rb
require "application_system_test_case"

class CreateEventTest < ApplicationSystemTestCase
  setup do
    @user = users(:one)
    sign_in @user
  end

  test "creates event successfully" do
    visit new_event_path

    fill_in "Name", with: "Company Party"
    fill_in "Event date", with: 1.month.from_now
    select "Corporate", from: "Event type"

    click_button "Create Event"

    assert_text "Event was successfully created"
    assert_text "Company Party"
  end

  test "shows validation errors" do
    visit new_event_path

    click_button "Create Event"

    assert_text "Name can't be blank"
  end
end
```

## Component Tests

Test ViewComponents:

```ruby
# test/components/event_card_component_test.rb
require "test_helper"

class EventCardComponentTest < ViewComponent::TestCase
  setup do
    @event = events(:one)
  end

  test "renders event name" do
    render_inline(EventCardComponent.new(event: @event))
    assert_text @event.name
  end

  test "renders status badge" do
    render_inline(EventCardComponent.new(event: @event))
    assert_selector ".badge"
  end

  test "shows days until for upcoming event" do
    upcoming = events(:upcoming)
    render_inline(EventCardComponent.new(event: upcoming))
    assert_text "days"
  end
end
```

## Test Helpers

### Shared Test Modules

```ruby
# test/support/tenant_isolation_test.rb
module TenantIsolationTest
  extend ActiveSupport::Concern

  included do
    test "excludes other tenant data" do
      result = subject_query
      assert_not_includes result.to_a, other_tenant_record
    end
  end
end

# Usage
# test/queries/active_events_query_test.rb
class ActiveEventsQueryTest < ActiveSupport::TestCase
  include TenantIsolationTest

  private

  def subject_query
    ActiveEventsQuery.new(account: accounts(:one)).call
  end

  def other_tenant_record
    events(:other_account)
  end
end
```

### Fixtures

```yaml
# test/fixtures/events.yml
one:
  account: one
  name: Annual Gala
  event_date: <%= 1.month.from_now.to_date %>
  status: 0

confirmed:
  account: one
  name: Confirmed Event
  event_date: <%= 2.months.from_now.to_date %>
  status: 1

past:
  account: one
  name: Past Event
  event_date: <%= 1.month.ago.to_date %>
  status: 2

other_account:
  account: two
  name: Other Account Event
  event_date: <%= 1.month.from_now.to_date %>
  status: 0
```

## Coverage Requirements

| Layer | Minimum Coverage |
|-------|-----------------|
| Models | 90% |
| Services | 95% |
| Queries | 90% |
| Controllers | 80% |
| Overall | 85% |

## Checklist

- [ ] Unit tests for all models
- [ ] Service tests cover success/failure paths
- [ ] Query tests check tenant isolation
- [ ] Integration tests for all endpoints
- [ ] Policy tests for authorization
- [ ] System tests for critical flows
- [ ] Component tests for ViewComponents
- [ ] Shared test modules for common patterns
- [ ] Fixtures for common states
