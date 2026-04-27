# Classic Refactoring Patterns

Use these during the REFACTOR phase after tests are green. Make one structural change at a time, then rerun the focused test.

## 1. Extract Method

Move a named chunk of controller, model, or service logic into a private method when the original method mixes setup, persistence, notification, and response handling.

```ruby
def create
  @entity = build_entity

  if @entity.save
    handle_successful_creation
    redirect_to @entity, notice: "Entity created successfully."
  else
    render :new, status: :unprocessable_entity
  end
end
```

## 2. Replace Conditional with Polymorphism

Replace large `case` or `if` dispatches with small classes that share a common interface.

```ruby
NOTIFIERS = {
  "email" => Notifications::EmailNotifier,
  "sms" => Notifications::SmsNotifier,
  "push" => Notifications::PushNotifier
}.freeze

def send_notification(user, type)
  NOTIFIERS.fetch(type).new(user).send
end
```

## 3. Introduce Parameter Object

Wrap long argument lists in a small object with named attributes.

```ruby
params = ReportParams.new(start_date:, end_date:, user_id:, format:)
ReportGenerator.new.generate(params)
```

## 4. Replace Magic Values with Named Constants

Use named constants for domain thresholds and time windows.

```ruby
TRIAL_PERIOD_DAYS = 14
FREE_ENTITY_LIMIT = 100
```

## 5. Decompose Conditional

Extract complex boolean logic into intention-revealing predicates.

```ruby
if eligible_for_premium_express?(order)
  apply_premium_express_discount(order)
elsif eligible_for_member_discount?(order)
  apply_member_discount(order)
else
  process_standard_order(order)
end
```

## 6. Remove Duplication

Extract repeated policy, query, or formatting logic into one method with a precise name.

```ruby
def update?
  admin_or_owner_of_draft?
end

def destroy?
  admin_or_owner_of_draft?
end
```

## 7. Simplify Guard Clauses

Flatten nested conditionals with early returns.

```ruby
def validate(user)
  return false if user.blank?
  return false if user.email.blank?

  user.email.match?(URI::MailTo::EMAIL_REGEXP)
end
```

## 8. Extract Service from Fat Model

Move orchestration out of very large models only when the service owns a coherent use case. Keep simple domain behavior on the model.

```ruby
class Orders::CreateService
  def call
    Order.transaction do
      order = Order.create!(params)
      Orders::ConfirmationService.call(order)
      Orders::InventoryService.call(order)
      order
    end
  end
end
```

## Output Format

```markdown
## Refactoring Complete: [Component Name]

### Changes Made
1. **Extract Method** - `Controller#action`
2. **Decompose Conditional** - `Policy#update?`

### Test Results
- `bin/rails test path/to/focused_test.rb`
- `bundle exec rubocop`

### Behavior Preserved
No behavior changes; tests pass without modifying expectations.
```
