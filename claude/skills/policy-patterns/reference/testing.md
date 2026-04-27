# Pundit Testing and Controller Usage Reference

## Pundit Test Helper Setup

```ruby
# test/support/pundit_helper.rb
module PunditTestHelper
  # Assert that a policy permits an action
  def assert_permit(user, record, action)
    policy = policy_class.new(user, record)
    assert policy.public_send(action),
      "Expected #{policy_class} to permit #{action} for #{user.inspect} on #{record.inspect}"
  end

  # Assert that a policy forbids an action
  def assert_forbid(user, record, action)
    policy = policy_class.new(user, record)
    assert_not policy.public_send(action),
      "Expected #{policy_class} to forbid #{action} for #{user.inspect} on #{record.inspect}"
  end

  private

  def policy_class
    self.class.name.sub(/Test$/, "").constantize
  end
end

# test/test_helper.rb
class ActiveSupport::TestCase
  include PunditTestHelper
end
```

## Complete Policy Test (EntityPolicy)

```ruby
# test/policies/entity_policy_test.rb
require "test_helper"

class EntityPolicyTest < ActiveSupport::TestCase
  setup do
    @owner = users(:owner)
    @entity = entities(:one) # belongs to @owner
  end

  # --- Unauthenticated visitor ---

  test "visitor can view index" do
    policy = EntityPolicy.new(nil, @entity)
    assert policy.index?
  end

  test "visitor can view show" do
    policy = EntityPolicy.new(nil, @entity)
    assert policy.show?
  end

  test "visitor cannot create" do
    policy = EntityPolicy.new(nil, @entity)
    assert_not policy.create?
    assert_not policy.new?
  end

  test "visitor cannot update" do
    policy = EntityPolicy.new(nil, @entity)
    assert_not policy.update?
    assert_not policy.edit?
  end

  test "visitor cannot destroy" do
    policy = EntityPolicy.new(nil, @entity)
    assert_not policy.destroy?
  end

  # --- Authenticated user (non-owner) ---

  test "authenticated user can view index and show" do
    user = users(:two)
    policy = EntityPolicy.new(user, @entity)

    assert policy.index?
    assert policy.show?
  end

  test "authenticated user can create" do
    user = users(:two)
    policy = EntityPolicy.new(user, @entity)

    assert policy.create?
    assert policy.new?
  end

  test "non-owner cannot update or destroy" do
    user = users(:two)
    policy = EntityPolicy.new(user, @entity)

    assert_not policy.update?
    assert_not policy.edit?
    assert_not policy.destroy?
  end

  # --- Entity owner ---

  test "owner can perform all actions" do
    policy = EntityPolicy.new(@owner, @entity)

    assert policy.index?
    assert policy.show?
    assert policy.create?
    assert policy.new?
    assert policy.update?
    assert policy.edit?
    assert policy.destroy?
  end

  # --- Scope ---

  test "scope returns only published entities" do
    scope = EntityPolicy::Scope.new(nil, Entity.all).resolve
    published = entities(:published)
    unpublished = entities(:unpublished)

    assert_includes scope, published
    assert_not_includes scope, unpublished
  end

  # --- Permitted attributes ---

  test "owner has full permitted attributes" do
    policy = EntityPolicy.new(@owner, @entity)

    assert_includes policy.permitted_attributes, :name
    assert_includes policy.permitted_attributes, :description
    assert_includes policy.permitted_attributes, :email
  end

  test "non-owner has no permitted attributes" do
    user = users(:two)
    policy = EntityPolicy.new(user, @entity)

    assert_empty policy.permitted_attributes
  end
end
```

## Test with Roles (SubmissionPolicy)

```ruby
# test/policies/submission_policy_test.rb
require "test_helper"

class SubmissionPolicyTest < ActiveSupport::TestCase
  setup do
    @author = users(:author)
    @entity_owner = users(:entity_owner)
    @admin = users(:admin)
    @other_user = users(:two)
    @entity = entities(:one) # belongs to @entity_owner
    @submission = submissions(:one) # belongs to @author, on @entity
  end

  # --- destroy? ---

  test "author can destroy own submission" do
    assert EntityPolicy.new(@author, @submission).class # just setup check
    policy = SubmissionPolicy.new(@author, @submission)
    assert policy.destroy?
  end

  test "entity owner can destroy submission" do
    policy = SubmissionPolicy.new(@entity_owner, @submission)
    assert policy.destroy?
  end

  test "admin can destroy submission" do
    policy = SubmissionPolicy.new(@admin, @submission)
    assert policy.destroy?
  end

  test "regular user cannot destroy submission" do
    policy = SubmissionPolicy.new(@other_user, @submission)
    assert_not policy.destroy?
  end

  # --- moderate? ---

  test "entity owner can moderate" do
    policy = SubmissionPolicy.new(@entity_owner, @submission)
    assert policy.moderate?
  end

  test "admin can moderate" do
    policy = SubmissionPolicy.new(@admin, @submission)
    assert policy.moderate?
  end

  test "author cannot moderate own submission" do
    policy = SubmissionPolicy.new(@author, @submission)
    assert_not policy.moderate?
  end

  # --- create? ---

  test "user can create first submission for entity" do
    new_submission = Submission.new(user: @other_user, entity: @entity)
    policy = SubmissionPolicy.new(@other_user, new_submission)
    assert policy.create?
  end

  test "user cannot create duplicate submission for same entity" do
    # @author already has @submission on @entity
    duplicate = Submission.new(user: @author, entity: @entity)
    policy = SubmissionPolicy.new(@author, duplicate)
    assert_not policy.create?
  end
end
```

## Test with Complex Conditions (BookingPolicy)

```ruby
# test/policies/booking_policy_test.rb
require "test_helper"

class BookingPolicyTest < ActiveSupport::TestCase
  setup do
    @customer = users(:customer)
    @entity_owner = users(:entity_owner)
    @entity = entities(:one) # belongs to @entity_owner
  end

  # --- cancel? ---

  test "customer can cancel booking more than 4 hours away" do
    booking = Booking.new(
      user: @customer,
      entity: @entity,
      booking_datetime: 6.hours.from_now,
      booking_date: Date.current
    )
    policy = BookingPolicy.new(@customer, booking)
    assert policy.cancel?
  end

  test "customer cannot cancel booking less than 4 hours away" do
    booking = Booking.new(
      user: @customer,
      entity: @entity,
      booking_datetime: 2.hours.from_now,
      booking_date: Date.current
    )
    policy = BookingPolicy.new(@customer, booking)
    assert_not policy.cancel?
  end

  test "customer cannot cancel past booking" do
    booking = Booking.new(
      user: @customer,
      entity: @entity,
      booking_datetime: 2.hours.ago,
      booking_date: 1.day.ago
    )
    policy = BookingPolicy.new(@customer, booking)
    assert_not policy.cancel?
  end

  test "entity owner can cancel regardless of time" do
    booking = Booking.new(
      user: @customer,
      entity: @entity,
      booking_datetime: 1.hour.from_now,
      booking_date: Date.current
    )
    policy = BookingPolicy.new(@entity_owner, booking)
    assert policy.cancel?
  end
end
```

## Controller with Authorization

```ruby
# app/controllers/entities_controller.rb
class EntitiesController < ApplicationController
  before_action :set_entity, only: [:show, :edit, :update, :destroy]

  def index
    @entities = policy_scope(Entity)
  end

  def show
    authorize @entity
  end

  def new
    @entity = Entity.new
    authorize @entity
  end

  def create
    @entity = current_user.entities.build(entity_params)
    authorize @entity

    if @entity.save
      redirect_to @entity, notice: "Entity created"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    authorize @entity
  end

  def update
    authorize @entity

    if @entity.update(permitted_attributes(@entity))
      redirect_to @entity, notice: "Entity updated"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    authorize @entity
    @entity.destroy
    redirect_to entities_path, notice: "Entity deleted"
  end

  private

  def set_entity
    @entity = Entity.find(params[:id])
  end

  def entity_params
    params.expect(entity: policy(@entity || Entity).permitted_attributes)
  end
end
```

## Error Handling in ApplicationController

```ruby
# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  include Pundit::Authorization

  rescue_from Pundit::NotAuthorizedError, with: :user_not_authorized

  private

  def user_not_authorized
    flash[:alert] = "You are not authorized to perform this action."
    redirect_back(fallback_location: root_path)
  end
end
```

## Custom Actions in Controllers

```ruby
# app/controllers/submissions_controller.rb
class SubmissionsController < ApplicationController
  def moderate
    @submission = Submission.find(params[:id])
    authorize @submission, :moderate?

    @submission.update(status: params[:status])
    redirect_to @submission.entity
  end

  def flag
    @submission = Submission.find(params[:id])
    authorize @submission, :flag?

    @submission.flags.create(user: current_user, reason: params[:reason])
    redirect_back(fallback_location: @submission.entity)
  end
end
```

## Testing Controller Authorization

```ruby
# test/controllers/entities_controller_test.rb
require "test_helper"

class EntitiesControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:one)
    @other_user = users(:two)
    @entity = entities(:one) # belongs to @user
    @other_entity = entities(:two) # belongs to @other_user
  end

  test "allows access to own entity" do
    sign_in @user
    get entity_path(@entity)
    assert_response :ok
  end

  test "denies access to other user entity" do
    sign_in @user
    get entity_path(@other_entity)
    assert_redirected_to root_path
  end

  test "allows deletion of own entity" do
    sign_in @user

    assert_difference("Entity.count", -1) do
      delete entity_path(@entity)
    end

    assert_redirected_to entities_path
  end

  test "denies deletion of other user entity" do
    sign_in @user

    assert_no_difference("Entity.count") do
      delete entity_path(@other_entity)
    end

    assert_redirected_to root_path
  end
end
```

## Policy Checks in Views

```erb
<%# app/views/entities/show.html.erb %>
<h1><%= @entity.name %></h1>

<% if policy(@entity).update? %>
  <%= link_to "Edit", edit_entity_path(@entity), class: "button" %>
<% end %>

<% if policy(@entity).destroy? %>
  <%= button_to "Delete", entity_path(@entity),
                method: :delete,
                data: { confirm: "Are you sure?" },
                class: "button is-danger" %>
<% end %>

<% if policy(Submission).create? %>
  <%= link_to "Submit content", new_entity_submission_path(@entity), class: "button" %>
<% end %>
```
