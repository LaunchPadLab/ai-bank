---
name: testing-patterns
description: Eight proven refactoring patterns with before/after Ruby examples for Rails applications. Use as a reference during the REFACTOR phase of TDD when applying Extract Method, Replace Conditional with Polymorphism, Introduce Parameter Object, Named Constants, Decompose Conditional, DRY, Guard Clauses, or Extract Service from Fat Model.
user-invocable: false
---
# Refactoring Patterns

## 1. Extract Method

**Before:**
```ruby
class EntitiesController < ApplicationController
  def create
    @entity = Entity.new(entity_params)
    @entity.status = 'pending'
    @entity.created_by = current_user.id

    if @entity.save
      ActivityLog.create!(
        action: 'entity_created',
        user: current_user,
        entity: @entity
      )

      EntityMailer.created(@entity).deliver_later

      redirect_to @entity, notice: 'Entity created successfully.'
    else
      render :new, status: :unprocessable_entity
    end
  end
end
```

**After:**
```ruby
class EntitiesController < ApplicationController
  def create
    @entity = build_entity

    if @entity.save
      handle_successful_creation
      redirect_to @entity, notice: 'Entity created successfully.'
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def build_entity
    Entity.new(entity_params).tap do |entity|
      entity.status = 'pending'
      entity.created_by = current_user.id
    end
  end

  def handle_successful_creation
    log_creation
    send_notification
  end

  def log_creation
    ActivityLog.create!(
      action: 'entity_created',
      user: current_user,
      entity: @entity
    )
  end

  def send_notification
    EntityMailer.created(@entity).deliver_later
  end
end
```

**Run tests:** `bin/rails test test/controllers/entities_controller_test.rb`

## 2. Replace Conditional with Polymorphism

**Before:**
```ruby
class NotificationService
  def send_notification(user, type)
    case type
    when 'email'
      UserMailer.notification(user).deliver_later
    when 'sms'
      SmsService.send(user.phone, "You have a notification")
    when 'push'
      PushNotificationService.send(user.device_token, "Notification")
    end
  end
end
```

**After:**
```ruby
# app/services/notifications/base_notifier.rb
class Notifications::BaseNotifier
  def initialize(user)
    @user = user
  end

  def send
    raise NotImplementedError
  end
end

# app/services/notifications/email_notifier.rb
class Notifications::EmailNotifier < Notifications::BaseNotifier
  def send
    UserMailer.notification(@user).deliver_later
  end
end

# app/services/notifications/sms_notifier.rb
class Notifications::SmsNotifier < Notifications::BaseNotifier
  def send
    SmsService.send(@user.phone, "You have a notification")
  end
end

# app/services/notifications/push_notifier.rb
class Notifications::PushNotifier < Notifications::BaseNotifier
  def send
    PushNotificationService.send(@user.device_token, "Notification")
  end
end

# app/services/notification_service.rb
class NotificationService
  NOTIFIERS = {
    'email' => Notifications::EmailNotifier,
    'sms' => Notifications::SmsNotifier,
    'push' => Notifications::PushNotifier
  }.freeze

  def send_notification(user, type)
    notifier_class = NOTIFIERS.fetch(type)
    notifier_class.new(user).send
  end
end
```

**Run tests:** `bin/rails test test/services/notification_service_test.rb`

## 3. Introduce Parameter Object

**Before:**
```ruby
class ReportGenerator
  def generate(start_date, end_date, user_id, format, include_details, sort_by)
    # Complex method with many parameters
  end
end

# Called like this:
ReportGenerator.new.generate(
  Date.today - 30.days,
  Date.today,
  current_user.id,
  'pdf',
  true,
  'created_at'
)
```

**After:**
```ruby
# app/services/report_params.rb
class ReportParams
  attr_reader :start_date, :end_date, :user_id, :format, :include_details, :sort_by

  def initialize(start_date:, end_date:, user_id:, format: 'pdf', include_details: false, sort_by: 'created_at')
    @start_date = start_date
    @end_date = end_date
    @user_id = user_id
    @format = format
    @include_details = include_details
    @sort_by = sort_by
  end
end

# app/services/report_generator.rb
class ReportGenerator
  def generate(params)
    # Cleaner method with single parameter object
  end
end

# Called like this:
params = ReportParams.new(
  start_date: Date.today - 30.days,
  end_date: Date.today,
  user_id: current_user.id,
  format: 'pdf',
  include_details: true
)
ReportGenerator.new.generate(params)
```

**Run tests:** `bin/rails test test/services/report_generator_test.rb`

## 4. Replace Magic Numbers with Named Constants

**Before:**
```ruby
class User < ApplicationRecord
  def premium?
    membership_level >= 3
  end

  def trial_expired?
    created_at < 14.days.ago && !premium?
  end

  def can_create_entities?
    entity_count < 100 || premium?
  end
end
```

**After:**
```ruby
class User < ApplicationRecord
  PREMIUM_MEMBERSHIP_LEVEL = 3
  TRIAL_PERIOD_DAYS = 14
  FREE_ENTITY_LIMIT = 100

  def premium?
    membership_level >= PREMIUM_MEMBERSHIP_LEVEL
  end

  def trial_expired?
    created_at < TRIAL_PERIOD_DAYS.days.ago && !premium?
  end

  def can_create_entities?
    entity_count < FREE_ENTITY_LIMIT || premium?
  end
end
```

**Run tests:** `bin/rails test test/models/user_test.rb`

## 5. Decompose Conditional

**Before:**
```ruby
class OrderProcessor
  def process(order)
    if order.total > 1000 && order.user.premium? && order.created_at > 1.day.ago
      apply_premium_express_discount(order)
    elsif order.total > 500 && order.user.member?
      apply_member_discount(order)
    else
      process_standard_order(order)
    end
  end
end
```

**After:**
```ruby
class OrderProcessor
  def process(order)
    if eligible_for_premium_express?(order)
      apply_premium_express_discount(order)
    elsif eligible_for_member_discount?(order)
      apply_member_discount(order)
    else
      process_standard_order(order)
    end
  end

  private

  def eligible_for_premium_express?(order)
    order.total > 1000 &&
      order.user.premium? &&
      order.created_at > 1.day.ago
  end

  def eligible_for_member_discount?(order)
    order.total > 500 && order.user.member?
  end
end
```

**Run tests:** `bin/rails test test/services/order_processor_test.rb`

## 6. Remove Duplication (DRY)

**Before:**
```ruby
class EntityPolicy < ApplicationPolicy
  def update?
    user.admin? || (record.user_id == user.id && record.status == 'draft')
  end

  def destroy?
    user.admin? || (record.user_id == user.id && record.status == 'draft')
  end
end
```

**After:**
```ruby
class EntityPolicy < ApplicationPolicy
  def update?
    admin_or_owner_of_draft?
  end

  def destroy?
    admin_or_owner_of_draft?
  end

  private

  def admin_or_owner_of_draft?
    user.admin? || owner_of_draft?
  end

  def owner_of_draft?
    record.user_id == user.id && record.status == 'draft'
  end
end
```

**Run tests:** `bin/rails test test/policies/entity_policy_test.rb`

## 7. Simplify Guard Clauses

**Before:**
```ruby
class UserValidator
  def validate(user)
    if user.present?
      if user.email.present?
        if user.email.match?(URI::MailTo::EMAIL_REGEXP)
          true
        else
          false
        end
      else
        false
      end
    else
      false
    end
  end
end
```

**After:**
```ruby
class UserValidator
  def validate(user)
    return false if user.blank?
    return false if user.email.blank?

    user.email.match?(URI::MailTo::EMAIL_REGEXP)
  end
end
```

**Run tests:** `bin/rails test test/validators/user_validator_test.rb`

## 8. Extract Service from Fat Model

**Before:**
```ruby
class Order < ApplicationRecord
  after_create :send_confirmation
  after_create :update_inventory
  after_create :notify_warehouse
  after_create :log_analytics

  def process_payment(payment_method)
    # 50 lines of payment logic
  end

  def calculate_shipping
    # 30 lines of shipping logic
  end

  def apply_discounts
    # 40 lines of discount logic
  end

  private

  def send_confirmation
    # ...
  end

  def update_inventory
    # ...
  end

  # Model is 300+ lines
end
```

**After:**
```ruby
# app/models/order.rb
class Order < ApplicationRecord
  # Just data model, no complex business logic
  belongs_to :user
  has_many :line_items

  validates :status, presence: true
end

# app/services/orders/create_service.rb
class Orders::CreateService < ApplicationService
  def initialize(params, user:)
    @params = params
    @user = user
  end

  def call
    Order.transaction do
      order = Order.create!(params)

      Orders::ConfirmationService.call(order)
      Orders::InventoryService.call(order)
      Orders::WarehouseNotifier.call(order)
      Orders::AnalyticsLogger.call(order)

      Success(order)
    end
  rescue ActiveRecord::RecordInvalid => e
    Failure(e.record.errors)
  end
end

# app/services/orders/payment_processor.rb
class Orders::PaymentProcessor < ApplicationService
  # Payment logic extracted
end

# app/services/orders/shipping_calculator.rb
class Orders::ShippingCalculator < ApplicationService
  # Shipping logic extracted
end

# app/services/orders/discount_applier.rb
class Orders::DiscountApplier < ApplicationService
  # Discount logic extracted
end
```

**Run tests:** `bin/rails test test/models/order_test.rb test/services/orders/`

## Refactoring Output Format

When completing a refactoring session, provide a summary using this template:

```markdown
## Refactoring Complete: [Component Name]

### Changes Made

1. **Extract Method** - `EntitiesController#create`
   - Extracted `build_entity` method
   - Extracted `handle_successful_creation` method
   - File: `app/controllers/entities_controller.rb`

2. **Simplify Conditional** - `EntityPolicy#update?`
   - Extracted `admin_or_owner_of_draft?` guard
   - File: `app/policies/entity_policy.rb`

### Test Results

All tests passing:
- `bin/rails test` - 156 tests, 0 failures
- `bundle exec rubocop -a` - No offenses
- `bin/brakeman` - No new warnings

### Metrics Improved

- Method complexity reduced: 23.5 -> 12.3 (Flog)
- Lines per method: 18 -> 8 (average)
- Duplication: 45 -> 12 (Flay)

### Behavior Preserved

No behavior changes - all tests pass without modification
```

## Additional Resources

- [domain-patterns.md](reference/domain-patterns.md) -- Refactoring workflow, code smell detection, one-change-at-a-time discipline, checklists, and when to stop refactoring