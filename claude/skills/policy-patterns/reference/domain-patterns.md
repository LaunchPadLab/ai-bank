# Policy Domain Patterns

## Rails 8 Authorization Notes

- **Scoped Policies:** Use `policy_scope` for index actions
- **Headless Policies:** Use `authorize :dashboard, :show?` for non-model actions
- **Permitted Attributes:** Define `permitted_attributes` for strong params

## Naming Convention

```
app/policies/
├── application_policy.rb
├── entity_policy.rb
├── submission_policy.rb
├── item_policy.rb
└── user_policy.rb

test/policies/
├── entity_policy_test.rb
├── submission_policy_test.rb
├── item_policy_test.rb
└── user_policy_test.rb
```

## Controller Authorization

Every controller action must call `authorize` or `policy_scope`:

```ruby
def index
  @entities = policy_scope(Entity)  # Scoped collection
end

def show
  authorize @entity  # Checks show?
end

def update
  authorize @entity  # Checks update?
  @entity.update(permitted_attributes(@entity))  # Uses policy's permitted_attributes
end
```

Always rescue `Pundit::NotAuthorizedError` in `ApplicationController`:

```ruby
rescue_from Pundit::NotAuthorizedError, with: :user_not_authorized

def user_not_authorized
  flash[:alert] = "You are not authorized to perform this action."
  redirect_back(fallback_location: root_path)
end
```

## Policy Testing Patterns

Required test contexts for every policy:
- Unauthenticated visitor (`user: nil`)
- Regular authenticated user
- Resource owner/author
- Admin (if applicable)
- Custom actions tested

```ruby
require "test_helper"

class EntityPolicyTest < ActiveSupport::TestCase
  setup do
    @entity = entities(:one)
  end

  test "unauthenticated visitor cannot create" do
    policy = EntityPolicy.new(nil, @entity)
    assert_not policy.create?
  end

  test "entity owner can update and destroy" do
    policy = EntityPolicy.new(users(:owner), @entity)
    assert policy.update?
    assert policy.destroy?
  end
end
```

## Commands

### Tests

- **All policies:** `bin/rails test test/policies/`
- **Specific policy:** `bin/rails test test/policies/entity_policy_test.rb`
- **Specific line:** `bin/rails test test/policies/entity_policy_test.rb:25`
- **Verbose format:** `bin/rails test test/policies/ -v`

### Generation

- **Generate a policy:** `bin/rails generate pundit:policy Entity`

### Linting

- **Lint policies:** `bundle exec rubocop -a app/policies/`
- **Lint tests:** `bundle exec rubocop -a test/policies/`

### Audit

- **Search for missing authorize:** `grep -r "def " app/controllers/ | grep -v "authorize"`

## Security Checklist

- [ ] Each controller action has its `authorize` or `policy_scope`
- [ ] Policies follow the principle of least privilege (deny by default)
- [ ] Tests cover all roles and edge cases
- [ ] `Scope` properly filters data based on user
- [ ] `permitted_attributes` are defined for updates
- [ ] Unauthenticated visitor (`user: nil`) tested
- [ ] Admin (if applicable) tested
- [ ] Custom actions tested

## Boundaries

- ✅ **Always:** Write policy tests, deny by default, verify every controller action has `authorize`
- ⚠️ **Ask first:** Before granting admin-level permissions, modifying existing policies
- 🚫 **Never:** Allow access by default, skip policy tests, hardcode user IDs
