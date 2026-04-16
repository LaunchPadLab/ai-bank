# Service Object Domain Patterns

## ApplicationService Base Class

```ruby
# app/services/application_service.rb
class ApplicationService
  def self.call(...)
    new(...).call
  end

  private

  def success(data = nil)
    Result.new(success: true, data: data, error: nil)
  end

  def failure(error)
    Result.new(success: false, data: nil, error: error)
  end

  # Ruby 3.2+ Data.define for immutable result objects
  Result = Data.define(:success, :data, :error) do
    def success? = success
    def failure? = !success
  end
end
```

## Service Patterns

### 1. Simple CRUD Service

```ruby
# app/services/submissions/create_service.rb
module Submissions
  class CreateService < ApplicationService
    def initialize(user:, entity:, params:)
      @user = user
      @entity = entity
      @params = params
    end

    def call
      return failure("You have already submitted") if already_submitted?

      submission = build_submission

      if submission.save
        update_entity_rating
        success(submission)
      else
        failure(submission.errors.full_messages.join(", "))
      end
    end

    private

    attr_reader :user, :entity, :params

    def already_submitted?
      entity.submissions.exists?(user: user)
    end

    def build_submission
      entity.submissions.build(params.merge(user: user))
    end

    def update_entity_rating
      Entities::CalculateRatingService.call(entity: entity)
    end
  end
end
```

### 2. Service with Transaction

```ruby
# app/services/orders/create_service.rb
module Orders
  class CreateService < ApplicationService
    def initialize(user:, cart:)
      @user = user
      @cart = cart
    end

    def call
      return failure("Cart is empty") if cart.empty?

      order = nil

      ActiveRecord::Base.transaction do
        order = create_order
        create_order_items(order)
        clear_cart
        charge_payment(order)
      end

      success(order)
    rescue ActiveRecord::RecordInvalid => e
      failure(e.message)
    rescue PaymentError => e
      failure("Payment error: #{e.message}")
    end

    private

    attr_reader :user, :cart

    def create_order
      user.orders.create!(total: cart.total, status: :pending)
    end

    def create_order_items(order)
      cart.items.each do |item|
        order.order_items.create!(
          product: item.product,
          quantity: item.quantity,
          price: item.price
        )
      end
    end

    def clear_cart
      cart.clear!
    end

    def charge_payment(order)
      PaymentGateway.charge(user: user, amount: order.total)
      order.update!(status: :paid)
    end
  end
end
```

### 3. Calculation/Query Service

```ruby
# app/services/entities/calculate_rating_service.rb
module Entities
  class CalculateRatingService < ApplicationService
    def initialize(entity:)
      @entity = entity
    end

    def call
      average = calculate_average_rating

      if entity.update(average_rating: average, submissions_count: submissions_count)
        success(average)
      else
        failure(entity.errors.full_messages.join(", "))
      end
    end

    private

    attr_reader :entity

    def calculate_average_rating
      return 0.0 if submissions_count.zero?

      entity.submissions.average(:rating).to_f.round(1)
    end

    def submissions_count
      @submissions_count ||= entity.submissions.count
    end
  end
end
```

### 4. Service with Injected Dependencies

```ruby
# app/services/notifications/send_service.rb
module Notifications
  class SendService < ApplicationService
    def initialize(user:, message:, notifier: default_notifier)
      @user = user
      @message = message
      @notifier = notifier
    end

    def call
      return failure("User has notifications disabled") unless user.notifications_enabled?

      notifier.deliver(user: user, message: message)
      success
    rescue NotificationError => e
      failure(e.message)
    end

    private

    attr_reader :user, :message, :notifier

    def default_notifier
      Rails.env.test? ? NullNotifier.new : PushNotifier.new
    end
  end
end
```

## Minitest Tests for Services

### Test Structure

```ruby
# test/services/entities/create_service_test.rb
require "test_helper"

class Entities::CreateServiceTest < ActiveSupport::TestCase
  setup do
    @user = users(:one)
    @params = { name: "Test Entity", description: "A test entity" }
  end

  test "creates an entity with valid parameters" do
    assert_difference("Entity.count", 1) do
      Entities::CreateService.call(user: @user, params: @params)
    end
  end

  test "returns success with valid parameters" do
    result = Entities::CreateService.call(user: @user, params: @params)
    assert result.success?
  end

  test "returns the created entity" do
    result = Entities::CreateService.call(user: @user, params: @params)
    assert_instance_of Entity, result.data
    assert result.data.persisted?
  end

  test "associates the entity with the user" do
    result = Entities::CreateService.call(user: @user, params: @params)
    assert_equal @user, result.data.user
  end

  test "does not create an entity with invalid parameters" do
    assert_no_difference("Entity.count") do
      Entities::CreateService.call(user: @user, params: { name: "" })
    end
  end

  test "returns failure with invalid parameters" do
    result = Entities::CreateService.call(user: @user, params: { name: "" })
    assert result.failure?
  end

  test "returns error message with invalid parameters" do
    result = Entities::CreateService.call(user: @user, params: { name: "" })
    assert_match(/Name/, result.error)
  end

  test "returns failure without user" do
    result = Entities::CreateService.call(user: nil, params: @params)
    assert result.failure?
  end

  test "returns authorization error without user" do
    result = Entities::CreateService.call(user: nil, params: @params)
    assert_equal "User not authorized", result.error
  end
end
```

### Testing Side Effects

```ruby
# test/services/submissions/create_service_test.rb
require "test_helper"

class Submissions::CreateServiceTest < ActiveSupport::TestCase
  setup do
    @user = users(:one)
    @entity = entities(:one)
    @params = { rating: 4, content: "Excellent!" }
  end

  test "updates the entity rating" do
    mock = Minitest::Mock.new
    mock.expect(:call, true, entity: @entity)

    Entities::CalculateRatingService.stub(:call, mock) do
      Submissions::CreateService.call(user: @user, entity: @entity, params: @params)
    end

    mock.verify
  end

  test "returns failure when user has already submitted" do
    Submission.create!(user: @user, entity: @entity, rating: 3, content: "Previous")
    result = Submissions::CreateService.call(user: @user, entity: @entity, params: @params)

    assert result.failure?
    assert_equal "You have already submitted", result.error
  end
end
```

### Testing Transactions

```ruby
# test/services/orders/create_service_test.rb
require "test_helper"

class Orders::CreateServiceTest < ActiveSupport::TestCase
  setup do
    @user = users(:one)
    @cart = carts(:with_items)
  end

  test "does not create order when payment fails (rollback)" do
    PaymentGateway.stub(:charge, ->(*) { raise PaymentError, "Card declined" }) do
      assert_no_difference("Order.count") do
        Orders::CreateService.call(user: @user, cart: @cart)
      end
    end
  end

  test "does not clear cart when payment fails (rollback)" do
    original_count = @cart.items.count

    PaymentGateway.stub(:charge, ->(*) { raise PaymentError, "Card declined" }) do
      Orders::CreateService.call(user: @user, cart: @cart)
    end

    assert_equal original_count, @cart.reload.items.count
  end

  test "returns failure when payment fails" do
    PaymentGateway.stub(:charge, ->(*) { raise PaymentError, "Card declined" }) do
      result = Orders::CreateService.call(user: @user, cart: @cart)
      assert result.failure?
      assert_match(/Card declined/, result.error)
    end
  end
end
```

## Usage in Controllers

```ruby
# app/controllers/entities_controller.rb
class EntitiesController < ApplicationController
  def create
    result = Entities::CreateService.call(
      user: current_user,
      params: entity_params
    )

    if result.success?
      redirect_to result.data, notice: "Entity created successfully"
    else
      @entity = Entity.new(entity_params)
      flash.now[:alert] = result.error
      render :new, status: :unprocessable_entity
    end
  end

  private

  def entity_params
    params.require(:entity).permit(:name, :description, :address, :phone)
  end
end
```

## When to Use a Service Object

### ✅ Use a service when:
- Logic involves multiple models
- Action requires a transaction
- There are side effects (emails, notifications, external APIs)
- Logic is too complex for a model
- You need to reuse logic (controller, job, console)

### ❌ Don't use a service when:
- It's simple CRUD without business logic
- Logic clearly belongs in the model
- You're creating a "wrapper" service without added value
