---
name: "rails-service-object"
description: "Creates plain Rails service objects for orchestration, transactions, side effects, and external systems with focused Minitest coverage. Use when logic spans multiple models or entry points, not for model-local behavior or simple CRUD."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools. -->

# Rails Service Object Pattern

## Overview

Service objects are plain Ruby collaborators for orchestration:
- Single responsibility (one public method: `#call`)
- Easy to test in isolation
- Reusable across controllers, jobs, rake tasks
- Clear input/output contract when Rails validations and exceptions are not enough
- Dependency injection only for real external boundaries

## When to Use Service Objects

| Scenario | Use Service Object? |
|----------|---------------------|
| Cohesive behavior on one model | No (use the model) |
| Simple CRUD operations | No (use controller/model) |
| Single model validation or state transition | No (use the model) |
| Multiple model interactions | Yes, when orchestration is clearer outside one aggregate |
| External API calls | Yes |
| Cross-model transaction or side effects | Yes |
| Logic shared across controllers/jobs | Yes |

## Workflow Checklist

```
Service Object Progress:
- [ ] Step 1: Define input/output contract
- [ ] Step 2: Create service test (RED)
- [ ] Step 3: Run test (fails - no service)
- [ ] Step 4: Create service file with empty #call
- [ ] Step 5: Run test (fails - wrong return)
- [ ] Step 6: Implement #call method
- [ ] Step 7: Run test (GREEN)
- [ ] Step 8: Add error case tests
- [ ] Step 9: Implement error handling
- [ ] Step 10: Final test run
```

## Step 1: Define Contract

```markdown
## Service: Orders::CreateService

### Purpose
Creates a new order with inventory validation and payment processing.

### Input
- user: User (required) - The user placing the order
- items: Array<Hash> (required) - Items to order [{product_id:, quantity:}]
- payment_method_id: Integer (optional) - Saved payment method

### Output

Prefer returning the domain object or letting Active Record validations/exceptions speak for themselves. Use a small result value only if the caller must branch on multiple failure modes.

Success:
- Order instance, or a result value with `success?`

Failure:
- Active Record validation/exception, or a result value with `error` and optional `code`

### Dependencies
- inventory_service: Checks product availability
- payment_gateway: Processes payment

### Side Effects
- Creates Order and OrderItem records
- Decrements inventory
- Charges payment method
- Sends confirmation email (async)
```

## Step 2: Service Test

Location: `test/services/orders/create_service_test.rb`

```ruby
# frozen_string_literal: true

require "test_helper"

class Orders::CreateServiceTest < ActiveSupport::TestCase
  setup do
    @user = users(:one)
    @product = products(:one) # inventory_count: 10
    @items = [{ product_id: @product.id, quantity: 2 }]
    @service = Orders::CreateService.new
  end

  test "returns success with valid inputs" do
    result = @service.call(user: @user, items: @items)
    assert_predicate result, :success?
  end

  test "creates an order with valid inputs" do
    assert_difference("Order.count", 1) do
      @service.call(user: @user, items: @items)
    end
  end

  test "returns the order with valid inputs" do
    result = @service.call(user: @user, items: @items)
    assert_kind_of Order, result.data
    assert_equal @user, result.data.user
  end

  test "returns failure with empty items" do
    result = @service.call(user: @user, items: [])
    assert_predicate result, :failure?
  end

  test "returns error message with empty items" do
    result = @service.call(user: @user, items: [])
    assert_equal "No items provided", result.error
  end

  test "returns failure with insufficient inventory" do
    items = [{ product_id: @product.id, quantity: 100 }]
    result = @service.call(user: @user, items: items)
    assert_predicate result, :failure?
  end

  test "does not create order with insufficient inventory" do
    items = [{ product_id: @product.id, quantity: 100 }]
    assert_no_difference("Order.count") do
      @service.call(user: @user, items: items)
    end
  end
end
```

## Step 3-6: Implement Service

Location: `app/services/orders/create_service.rb`

```ruby
# frozen_string_literal: true

module Orders
  Result = Data.define(:success, :data, :error, :code) do
    def success? = success
    def failure? = !success
  end

  class CreateService
    def initialize(inventory_service: InventoryService.new,
                   payment_gateway: PaymentGateway.new)
      @inventory_service = inventory_service
      @payment_gateway = payment_gateway
    end

    def call(user:, items:, payment_method_id: nil)
      return failure('No items provided', :empty_items) if items.empty?
      return failure('Insufficient inventory', :insufficient_inventory) unless inventory_available?(items)

      order = create_order(user, items)
      process_payment(order, payment_method_id) if payment_method_id

      success(order)
    rescue ActiveRecord::RecordInvalid => e
      failure(e.message, :validation_failed)
    rescue PaymentError => e
      failure(e.message, :payment_failed)
    end

    private

    attr_reader :inventory_service, :payment_gateway

    def inventory_available?(items)
      items.all? do |item|
        inventory_service.available?(item[:product_id], item[:quantity])
      end
    end

    def create_order(user, items)
      ActiveRecord::Base.transaction do
        order = Order.create!(user: user, status: :pending)

        items.each do |item|
          order.order_items.create!(
            product_id: item[:product_id],
            quantity: item[:quantity]
          )
          inventory_service.decrement(item[:product_id], item[:quantity])
        end

        order
      end
    end

    def process_payment(order, payment_method_id)
      payment_gateway.charge(
        amount: order.total,
        payment_method_id: payment_method_id
      )
      order.update!(status: :paid)
    end

    def success(data)
      Result.new(success: true, data: data)
    end

    def failure(error, code = :unknown)
      Result.new(success: false, error: error, code: code)
    end
  end
end
```

## Optional Result Object

Do not create a global result wrapper by default. If a service has meaningful recoverable failure modes, define a small value object close to the service or reuse an existing project-level result type.

```ruby
# frozen_string_literal: true

module Orders
  Result = Data.define(:success, :data, :error, :code) do
    def success? = success
    def failure? = !success
  end
end
```

## Calling Services

### From Controllers

```ruby
class OrdersController < ApplicationController
  def create
    result = Orders::CreateService.new.call(
      user: current_user,
      items: order_params[:items],
      payment_method_id: order_params[:payment_method_id]
    )

    if result.success?
      render json: result.data, status: :created
    else
      render json: { error: result.error }, status: :unprocessable_entity
    end
  end
end
```

### From Jobs

```ruby
class ProcessOrderJob < ApplicationJob
  def perform(user_id, items)
    user = User.find(user_id)
    result = Orders::CreateService.new.call(user: user, items: items)

    unless result.success?
      Rails.logger.error("Order failed: #{result.error}")
      # Handle failure (retry, notify, etc.)
    end
  end
end
```

## Testing with Mocked Dependencies

```ruby
class Orders::CreateServiceWithMocksTest < ActiveSupport::TestCase
  setup do
    @inventory_service = Minitest::Mock.new
    @payment_gateway = Minitest::Mock.new
    @service = Orders::CreateService.new(
      inventory_service: @inventory_service,
      payment_gateway: @payment_gateway
    )
  end

  test "calls inventory and payment services" do
    @inventory_service.expect :available?, true, [Integer, Integer]
    @inventory_service.expect :decrement, true, [Integer, Integer]
    @payment_gateway.expect :charge, true, [Hash]

    # ... exercise and verify ...
    @inventory_service.verify
    @payment_gateway.verify
  end
end
```

## Directory Structure

```
app/services/
├── orders/
│   ├── create_service.rb
│   ├── cancel_service.rb
│   └── refund_service.rb
├── users/
│   ├── register_service.rb
│   └── update_profile_service.rb
└── payments/
    ├── charge_service.rb
    └── refund_service.rb
```

## Conventions

1. **Naming**: `VerbNounService` (e.g., `CreateOrderService`)
2. **Location**: `app/services/[namespace]/[name]_service.rb`
3. **Interface**: Single public method `#call`
4. **Return**: Prefer a domain object, boolean, or existing project result type
5. **Dependencies**: Inject only external boundaries or expensive collaborators
6. **Errors**: Let Rails validations/exceptions stand unless the caller needs typed failures

## Anti-Patterns to Avoid

1. **God service**: Too many responsibilities
2. **Hidden dependencies**: Using globals instead of injection
3. **No return contract**: Returning different types
4. **Result object ceremony**: Wrapping simple Active Record outcomes without a real caller need
5. **Model-local behavior in services**: Put cohesive aggregate behavior on the model

## Additional Resources

- [Domain Patterns](reference/domain-patterns.md) — transaction, dependency-injection, side-effect testing, and controller integration patterns for cases where a service object is justified
