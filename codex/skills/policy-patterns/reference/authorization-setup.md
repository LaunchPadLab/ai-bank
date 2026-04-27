# Authorization with Pundit for Rails 8

## Overview

Pundit provides policy-based authorization:
- Plain Ruby policy objects
- Convention over configuration
- Easy to test
- Scoped queries for collections
- Works with any authentication system

## Quick Start

```bash
# Add to Gemfile
bundle add pundit

# Generate base files
bin/rails generate pundit:install

# Generate policy for model
bin/rails generate pundit:policy Event
```

## Project Structure

```
app/
├── policies/
│   ├── application_policy.rb    # Base policy
│   ├── event_policy.rb
│   ├── vendor_policy.rb
│   └── user_policy.rb
test/policies/
├── event_policy_test.rb
├── vendor_policy_test.rb
└── user_policy_test.rb
```

## TDD Workflow

```
Authorization Progress:
- [ ] Step 1: Write policy test (RED)
- [ ] Step 2: Run test (fails)
- [ ] Step 3: Implement policy
- [ ] Step 4: Run test (GREEN)
- [ ] Step 5: Add policy to controller
- [ ] Step 6: Test integration
```

## Base Policy

```ruby
# app/policies/application_policy.rb
class ApplicationPolicy
  attr_reader :user, :record

  def initialize(user, record)
    @user = user
    @record = record
  end

  # Default: deny all
  def index?
    false
  end

  def show?
    false
  end

  def create?
    false
  end

  def new?
    create?
  end

  def update?
    false
  end

  def edit?
    update?
  end

  def destroy?
    false
  end

  class Scope
    def initialize(user, scope)
      @user = user
      @scope = scope
    end

    def resolve
      raise NotImplementedError, "Define #resolve in #{self.class}"
    end

    private

    attr_reader :user, :scope
  end
end
```

## Policy Testing

### Policy Test

```ruby
# test/policies/event_policy_test.rb
require "test_helper"

class EventPolicyTest < ActiveSupport::TestCase
  setup do
    @user = users(:one)
    @account = @user.account
    @other_user = users(:two) # different account
    @event = events(:one)     # belongs to @account
  end

  test "index permits any authenticated user" do
    assert EventPolicy.new(@user, Event).index?
  end

  test "show permits user from same account" do
    assert EventPolicy.new(@user, @event).show?
  end

  test "show denies user from different account" do
    refute EventPolicy.new(@other_user, @event).show?
  end

  test "create permits user from same account" do
    assert EventPolicy.new(@user, Event.new(account: @account)).create?
  end

  test "update permits user from same account" do
    assert EventPolicy.new(@user, @event).update?
  end

  test "update denies user from different account" do
    refute EventPolicy.new(@other_user, @event).update?
  end

  test "destroy permits user from same account" do
    assert EventPolicy.new(@user, @event).destroy?
  end

  test "destroy denies user from different account" do
    refute EventPolicy.new(@other_user, @event).destroy?
  end

  test "scope returns events for user's account only" do
    other_event = events(:other_account) # different account

    scope = EventPolicy::Scope.new(@user, Event).resolve

    assert_includes scope, @event
    refute_includes scope, other_event
  end
end
```

## Policy Implementation

### Basic Policy

```ruby
# app/policies/event_policy.rb
class EventPolicy < ApplicationPolicy
  def index?
    true  # Any authenticated user can list
  end

  def show?
    owner?
  end

  def create?
    true  # Any authenticated user can create
  end

  def update?
    owner?
  end

  def destroy?
    owner?
  end

  private

  def owner?
    record.account_id == user.account_id
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      scope.where(account_id: user.account_id)
    end
  end
end
```

### Role-Based Policy

```ruby
# app/policies/event_policy.rb
class EventPolicy < ApplicationPolicy
  def index?
    true
  end

  def show?
    owner? || admin?
  end

  def create?
    member_or_above?
  end

  def update?
    owner_or_admin?
  end

  def destroy?
    admin?
  end

  # Custom action
  def publish?
    owner_or_admin? && record.draft?
  end

  def duplicate?
    owner?
  end

  private

  def owner?
    record.account_id == user.account_id
  end

  def admin?
    user.admin?
  end

  def member_or_above?
    user.member? || user.admin?
  end

  def owner_or_admin?
    owner? || admin?
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      if user.admin?
        scope.all
      else
        scope.where(account_id: user.account_id)
      end
    end
  end
end
```

### Policy with Conditions

```ruby
# app/policies/event_policy.rb
class EventPolicy < ApplicationPolicy
  def update?
    owner? && !record.locked?
  end

  def destroy?
    owner? && record.destroyable?
  end

  def cancel?
    owner? && record.can_cancel?
  end

  def restore?
    owner? && record.cancelled?
  end
end
```

## Controller Integration

### Basic Usage

```ruby
# app/controllers/events_controller.rb
class EventsController < ApplicationController
  def index
    @events = policy_scope(Event)
  end

  def show
    @event = Event.find(params[:id])
    authorize @event
  end

  def new
    @event = current_account.events.build
    authorize @event
  end

  def create
    @event = current_account.events.build(event_params)
    authorize @event

    if @event.save
      redirect_to @event, notice: t(".success")
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    @event = Event.find(params[:id])
    authorize @event
  end

  def update
    @event = Event.find(params[:id])
    authorize @event

    if @event.update(event_params)
      redirect_to @event, notice: t(".success")
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @event = Event.find(params[:id])
    authorize @event
    @event.destroy
    redirect_to events_path, notice: t(".success")
  end
end
```

### Custom Action Authorization

```ruby
class EventsController < ApplicationController
  def publish
    @event = Event.find(params[:id])
    authorize @event, :publish?

    if @event.publish!
      redirect_to @event, notice: t(".success")
    else
      redirect_to @event, alert: t(".failure")
    end
  end

  def duplicate
    @event = Event.find(params[:id])
    authorize @event, :duplicate?

    @new_event = @event.duplicate
    redirect_to edit_event_path(@new_event)
  end
end
```

### Ensuring Authorization

```ruby
# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  include Pundit::Authorization

  after_action :verify_authorized, except: :index
  after_action :verify_policy_scoped, only: :index

  rescue_from Pundit::NotAuthorizedError, with: :user_not_authorized

  private

  def user_not_authorized
    flash[:alert] = t("pundit.not_authorized")
    redirect_back(fallback_location: root_path)
  end
end
```

### Skip Authorization

```ruby
class HomeController < ApplicationController
  skip_after_action :verify_authorized, only: [:index, :about]
  skip_after_action :verify_policy_scoped, only: [:index, :about]

  def index
    # Public page, no authorization needed
  end
end
```

## View Integration

### Conditional Display

```erb
<%# app/views/events/show.html.erb %>
<h1><%= @event.name %></h1>

<% if policy(@event).edit? %>
  <%= link_to t("common.edit"), edit_event_path(@event) %>
<% end %>

<% if policy(@event).destroy? %>
  <%= button_to t("common.delete"), @event, method: :delete,
                data: { confirm: t("common.confirm_delete") } %>
<% end %>

<% if policy(@event).publish? %>
  <%= button_to t(".publish"), publish_event_path(@event), method: :post %>
<% end %>
```

### In Components

```ruby
# app/components/event_actions_component.rb
class EventActionsComponent < ApplicationComponent
  include Pundit::Authorization

  def initialize(event:, user:)
    @event = event
    @user = user
  end

  def can_edit?
    policy.edit?
  end

  def can_delete?
    policy.destroy?
  end

  def can_publish?
    policy.publish?
  end

  private

  def policy
    @policy ||= EventPolicy.new(@user, @event)
  end
end
```

## Headless Policies

For actions not tied to a specific record:

```ruby
# app/policies/dashboard_policy.rb
class DashboardPolicy < ApplicationPolicy
  def initialize(user, _record = nil)
    @user = user
  end

  def show?
    true
  end

  def admin_panel?
    user.admin?
  end

  def export_data?
    user.admin? || user.manager?
  end
end
```

```ruby
# Controller
class DashboardController < ApplicationController
  def show
    authorize :dashboard, :show?
  end

  def admin_panel
    authorize :dashboard, :admin_panel?
  end
end
```

## Permitted Attributes

### In Policy

```ruby
# app/policies/event_policy.rb
class EventPolicy < ApplicationPolicy
  def permitted_attributes
    if user.admin?
      [:name, :event_date, :status, :budget_cents, :internal_notes]
    else
      [:name, :event_date, :status, :budget_cents]
    end
  end

  def permitted_attributes_for_create
    [:name, :event_date]
  end

  def permitted_attributes_for_update
    permitted_attributes
  end
end
```

### In Controller

```ruby
class EventsController < ApplicationController
  def create
    @event = current_account.events.build(permitted_attributes(@event))
    authorize @event
    # ...
  end

  def update
    @event = Event.find(params[:id])
    authorize @event

    if @event.update(permitted_attributes(@event))
      # ...
    end
  end
end
```

## Nested Resource Policies

```ruby
# app/policies/comment_policy.rb
class CommentPolicy < ApplicationPolicy
  def create?
    # User can comment on events they can view
    EventPolicy.new(user, record.event).show?
  end

  def destroy?
    owner? || event_owner?
  end

  private

  def owner?
    record.user_id == user.id
  end

  def event_owner?
    record.event.account_id == user.account_id
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      # Only comments on events user can see
      scope.joins(:event).where(events: { account_id: user.account_id })
    end
  end
end
```

## Testing Controller Authorization

```ruby
# test/integration/events_authorization_test.rb
require "test_helper"

class EventsAuthorizationTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:one)
    @event = events(:one)               # belongs to @user's account
    @other_event = events(:other_account) # belongs to different account
    sign_in @user
  end

  test "allows access to own events" do
    get event_path(@event)
    assert_response :ok
  end

  test "denies access to other's events" do
    get event_path(@other_event)
    assert_redirected_to root_path
  end

  test "allows deletion of own events" do
    delete event_path(@event)
    assert_redirected_to events_path
    refute Event.exists?(@event.id)
  end

  test "denies deletion of other's events" do
    delete event_path(@other_event)
    assert_redirected_to root_path
    assert Event.exists?(@other_event.id)
  end
end
```

## Error Messages

```yaml
# config/locales/en.yml
en:
  pundit:
    not_authorized: You are not authorized to perform this action.
    event_policy:
      show?: You cannot view this event.
      update?: You cannot edit this event.
      destroy?: You cannot delete this event.
      publish?: This event cannot be published.
```

```ruby
# Custom error handling
rescue_from Pundit::NotAuthorizedError do |exception|
  policy_name = exception.policy.class.to_s.underscore
  message = t("#{policy_name}.#{exception.query}", scope: "pundit", default: :default)
  redirect_back(fallback_location: root_path, alert: message)
end
```

## Checklist

- [ ] Policy test written first (RED)
- [ ] Policy inherits from ApplicationPolicy
- [ ] Scope defined for collections
- [ ] Controller uses `authorize` and `policy_scope`
- [ ] `verify_authorized` after_action enabled
- [ ] Views use `policy(@record).action?`
- [ ] Error handling configured
- [ ] Multi-tenancy enforced in Scope
- [ ] All tests GREEN
