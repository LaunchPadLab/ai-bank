---
name: red-test-patterns
description: Provides RED phase test templates for writing failing Minitest tests before implementation. Use when starting TDD for a new model, service object, controller, view component, policy, or adding methods to existing models. Covers test structure, expected failure messages, fixture setup, and run commands for each component type.
user-invocable: false
---

# RED Phase Test Patterns by Component Type

Use this for the RED step of TDD when the goal is to write the first failing test. Use `testing-patterns` for broader Rails test mechanics and `tdd-cycle` for the complete Red-Green-Refactor workflow.

## New Model

```ruby
# test/models/membership_test.rb
require "test_helper"

# This model doesn't exist yet - the test should fail with:
# "NameError: uninitialized constant Membership"

class MembershipTest < ActiveSupport::TestCase
  # --- Associations ---

  test "belongs to user" do
    membership = memberships(:active)
    assert_respond_to membership, :user
    assert_instance_of User, membership.user
  end

  test "belongs to tier" do
    membership = memberships(:active)
    assert_respond_to membership, :tier
    assert_instance_of Tier, membership.tier
  end

  # --- Validations ---

  test "requires starts_at" do
    membership = Membership.new(starts_at: nil)
    assert_not membership.valid?
    assert membership.errors.added?(:starts_at, :blank)
  end

  test "requires status" do
    membership = Membership.new(status: nil)
    assert_not membership.valid?
    assert membership.errors.added?(:status, :blank)
  end

  # --- Instance methods ---

  test "#active? returns true when status is active and not expired" do
    membership = Membership.new(status: "active", ends_at: 1.month.from_now)
    assert membership.active?
  end

  test "#active? returns false when status is cancelled" do
    membership = Membership.new(status: "cancelled")
    assert_not membership.active?
  end
end
```

## New Service

```ruby
# test/services/transaction_processor_test.rb
require "test_helper"

# This service doesn't exist yet - the test should fail with:
# "NameError: uninitialized constant TransactionProcessor"

class TransactionProcessorTest < ActiveSupport::TestCase
  setup do
    @order = orders(:pending)
    @payment_method = payment_methods(:valid_card)
  end

  test "#process with valid payment method returns success" do
    processor = TransactionProcessor.new(@order)
    result = processor.process(@payment_method)

    assert result.success?
    assert result.transaction_id.present?
  end

  test "#process with valid payment method marks order as paid" do
    processor = TransactionProcessor.new(@order)
    processor.process(@payment_method)

    assert_equal "paid", @order.reload.status
  end

  test "#process with insufficient funds returns failure" do
    payment_method = payment_methods(:insufficient_funds)
    processor = TransactionProcessor.new(@order)
    result = processor.process(payment_method)

    assert result.failure?
    assert_equal "Insufficient funds", result.error
  end

  test "#process with insufficient funds does not change order status" do
    payment_method = payment_methods(:insufficient_funds)
    processor = TransactionProcessor.new(@order)

    assert_no_changes -> { @order.reload.status } do
      processor.process(payment_method)
    end
  end
end
```

## New Method on Existing Model

```ruby
# test/models/user_test.rb
require "test_helper"

class UserTest < ActiveSupport::TestCase
  # Existing tests...

  # NEW: This method doesn't exist yet
  # Should fail with: "NoMethodError: undefined method 'membership_status'"

  test "#membership_status returns :active when user has active membership" do
    user = users(:with_active_membership)
    assert_equal :active, user.membership_status
  end

  test "#membership_status returns :expired when user has expired membership" do
    user = users(:with_expired_membership)
    assert_equal :expired, user.membership_status
  end

  test "#membership_status returns :none when user has no membership" do
    user = users(:without_membership)
    assert_equal :none, user.membership_status
  end
end
```

## New Controller

```ruby
# test/controllers/api/memberships_controller_test.rb
require "test_helper"

# This route and controller don't exist yet

class Api::MembershipsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:one)
    @tier = tiers(:premium)
    sign_in @user
  end

  test "POST /api/memberships creates a new membership" do
    assert_difference("Membership.count", 1) do
      post api_memberships_path, params: { membership: { tier_id: @tier.id } }
    end
  end

  test "POST /api/memberships returns created status with membership data" do
    post api_memberships_path, params: { membership: { tier_id: @tier.id } }

    assert_response :created

    json = JSON.parse(response.body)
    assert_equal @tier.id, json["tier_id"]
  end

  test "POST /api/memberships with existing active membership returns error" do
    # User already has an active membership via fixtures
    @user = users(:with_active_membership)
    sign_in @user

    post api_memberships_path, params: { membership: { tier_id: @tier.id } }

    assert_response :unprocessable_entity

    json = JSON.parse(response.body)
    assert_match(/already has an active membership/, json["error"])
  end
end
```

## New View Component

```ruby
# test/components/tier_card_component_test.rb
require "test_helper"

# This component doesn't exist yet

class TierCardComponentTest < ViewComponent::TestCase
  setup do
    @tier = tiers(:premium) # name: "Premium", price: 29.99
  end

  test "displays the tier name" do
    render_inline(TierCardComponent.new(tier: @tier))

    assert_text "Premium"
  end

  test "displays the formatted price" do
    render_inline(TierCardComponent.new(tier: @tier))

    assert_text "29.99"
  end

  test "includes a subscribe button" do
    doc = render_inline(TierCardComponent.new(tier: @tier))

    assert_selector 'button[data-action="subscribe"]'
  end

  test "shows original price crossed out when tier has discount" do
    tier = tiers(:discounted) # original_price: 39.99, price: 29.99

    doc = render_inline(TierCardComponent.new(tier: tier))

    assert_selector ".original-price.line-through"
    assert_text "39.99"
  end

  test "displays discount badge when tier has discount" do
    tier = tiers(:discounted)

    render_inline(TierCardComponent.new(tier: tier))

    assert_selector ".discount-badge"
  end
end
```

## New Policy

```ruby
# test/policies/membership_policy_test.rb
require "test_helper"

# This policy doesn't exist yet

class MembershipPolicyTest < ActiveSupport::TestCase
  setup do
    @owner = users(:one)
    @membership = memberships(:active) # belongs to @owner
  end

  # --- Membership owner ---

  test "owner can show membership" do
    policy = MembershipPolicy.new(@owner, @membership)
    assert policy.show?
  end

  test "owner can cancel membership" do
    policy = MembershipPolicy.new(@owner, @membership)
    assert policy.cancel?
  end

  test "owner cannot destroy membership" do
    policy = MembershipPolicy.new(@owner, @membership)
    assert_not policy.destroy?
  end

  # --- Non-owner ---

  test "non-owner cannot show membership" do
    other_user = users(:two)
    policy = MembershipPolicy.new(other_user, @membership)
    assert_not policy.show?
  end

  test "non-owner cannot cancel membership" do
    other_user = users(:two)
    policy = MembershipPolicy.new(other_user, @membership)
    assert_not policy.cancel?
  end

  test "non-owner cannot destroy membership" do
    other_user = users(:two)
    policy = MembershipPolicy.new(other_user, @membership)
    assert_not policy.destroy?
  end

  # --- Admin ---

  test "admin can show membership" do
    admin = users(:admin)
    policy = MembershipPolicy.new(admin, @membership)
    assert policy.show?
  end

  test "admin can cancel membership" do
    admin = users(:admin)
    policy = MembershipPolicy.new(admin, @membership)
    assert policy.cancel?
  end

  test "admin can destroy membership" do
    admin = users(:admin)
    policy = MembershipPolicy.new(admin, @membership)
    assert policy.destroy?
  end
end
```

## Fixtures for RED Tests

When writing a RED test, also create the necessary fixtures. The fixtures will also fail until the model and migration are created.

```yaml
# test/fixtures/memberships.yml
active:
  user: one
  tier: premium
  status: active
  starts_at: <%= Time.current %>
  ends_at: <%= 1.month.from_now %>

expired:
  user: two
  tier: premium
  status: expired
  starts_at: <%= 2.months.ago %>
  ends_at: <%= 1.day.ago %>

cancelled:
  user: three
  tier: premium
  status: cancelled
  starts_at: <%= 1.month.ago %>
  ends_at: <%= 1.month.from_now %>
  cancelled_at: <%= Time.current %>
```

## Running RED Tests

```bash
# Run a single test file
bin/rails test test/models/membership_test.rb --verbose

# Run a specific test by name
bin/rails test test/models/membership_test.rb -n "test_requires_starts_at"

# Run a specific test by line number
bin/rails test test/models/membership_test.rb:15

# Run all tests in a directory
bin/rails test test/models/ --verbose

# Expected RED output (model doesn't exist yet):
# Error: NameError: uninitialized constant Membership
```

## Reference

- [Domain Patterns](reference/domain-patterns.md) — Fixture patterns, model/controller/system/job/mailer test patterns, testing auth, Turbo streams, JSON APIs, concerns, performance testing, common patterns catalog