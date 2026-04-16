---
name: tdd-cycle
description: Guides Test-Driven Development workflow with Red-Green-Refactor cycle. Use when the user wants to implement a feature using TDD, write tests first, follow test-driven practices, or mentions red-green-refactor.
allowed-tools: Read, Write, Edit, Bash
disable-model-invocation: true
argument-hint: "[component-name]"
---

# TDD Cycle Skill

**Component to implement: $ARGUMENTS**

## Overview

This skill guides you through the Test-Driven Development cycle:
1. **RED**: Write a failing test that describes desired behavior
2. **GREEN**: Write minimal code to pass the test
3. **REFACTOR**: Improve code while keeping tests green

## Workflow Checklist

Copy and track progress:

```
TDD Progress:
- [ ] Step 1: Understand the requirement
- [ ] Step 2: Choose test type (unit/controller/system)
- [ ] Step 3: Write failing test (RED)
- [ ] Step 4: Verify test fails correctly
- [ ] Step 5: Implement minimal code (GREEN)
- [ ] Step 6: Verify test passes
- [ ] Step 7: Refactor if needed
- [ ] Step 8: Verify tests still pass
```

## Step 1: Requirement Analysis

Before writing any code, understand:
- What is the expected input?
- What is the expected output/behavior?
- What are the edge cases?
- What errors should be handled?

Ask clarifying questions if requirements are ambiguous.

## Step 2: Choose Test Type

| Test Type | Use For | Location | Example |
|-----------|---------|----------|---------|
| Model test | Validations, scopes, instance methods | `test/models/` | Testing `User#full_name` |
| Controller test | API endpoints, HTTP responses | `test/controllers/` | Testing `POST /api/users` |
| System test | Full user flows with JavaScript | `test/system/` | Testing login flow |
| Service test | Business logic, complex operations | `test/services/` | Testing `CreateOrderService` |
| Job test | Background job behavior | `test/jobs/` | Testing `SendEmailJob` |

## Step 3: Write Failing Test (RED)

### Test Structure

```ruby
# frozen_string_literal: true

require "test_helper"

class ClassNameTest < ActiveSupport::TestCase
  setup do
    @instance = class_names(:one)
  end

  test "method_name returns expected value when condition is met" do
    assert_equal expected_value, @instance.method_name
  end

  test "method_name raises error on edge case" do
    assert_raises(SpecificError) { @instance.method_name }
  end
end
```

### Good Test Characteristics

- **One behavior per test**: Each `test` block tests one thing
- **Clear description**: Test name reads as a sentence describing behavior
- **Minimal setup**: Only create data needed for the specific test
- **Fast execution**: Avoid unnecessary database hits, use fixtures
- **Independent**: Tests don't depend on order or shared state

## Step 4: Verify Failure

Run the test:
```bash
bin/rails test path/to/test.rb --verbose
```

The test MUST fail with a clear message indicating:
- What was expected
- What was received (or that the method/class doesn't exist)
- Why it failed

**Important**: If the test passes immediately, you're not doing TDD. Either:
- The behavior already exists (check if this is intentional)
- The test is wrong (not testing what you think)

## Step 5: Implement (GREEN)

Write the MINIMUM code to pass:
- No optimization yet
- No edge case handling (unless that's what you're testing)
- No refactoring
- Just make it work

```ruby
def full_name
  "#{first_name} #{last_name}"
end
```

## Step 6: Verify Pass

Run the test again:
```bash
bin/rails test path/to/test.rb --verbose
```

It MUST pass. If it fails:
1. Read the error carefully
2. Fix the implementation (not the test, unless the test was wrong)
3. Run again

## Step 7: Refactor

Now improve the code while keeping tests green:

### Refactoring Targets
- **Extract methods**: Long methods → smaller focused methods
- **Improve naming**: Unclear names → intention-revealing names
- **Remove duplication**: Repeated code → shared abstractions
- **Simplify logic**: Complex conditionals → cleaner patterns

### Refactoring Rules
1. Make ONE change at a time
2. Run tests after EACH change
3. If tests fail, undo and try different approach
4. Stop when code is clean (don't over-engineer)

## Step 8: Final Verification

Run all related tests:
```bash
bin/rails test test/models/user_test.rb
```

All tests must pass. If any fail:
- Undo recent changes
- Try a different refactoring approach
- Consider if the failing test reveals a real bug

## Common Patterns

### Testing Validations

```ruby
class UserValidationTest < ActiveSupport::TestCase
  test "requires email" do
    user = User.new(email: nil)
    assert_not user.valid?
    assert_includes user.errors[:email], "can't be blank"
  end

  test "requires unique email (case insensitive)" do
    existing = users(:one)
    user = User.new(email: existing.email.upcase)
    assert_not user.valid?
  end

  test "enforces max length on name" do
    user = User.new(name: "a" * 101)
    assert_not user.valid?
    assert_includes user.errors[:name], "is too long (maximum is 100 characters)"
  end
end
```

### Testing Associations

```ruby
class UserAssociationTest < ActiveSupport::TestCase
  test "belongs to organization" do
    user = users(:one)
    assert_instance_of Organization, user.organization
  end

  test "has many posts" do
    user = users(:one)
    assert_respond_to user, :posts
  end

  test "destroys dependent posts" do
    user = users(:one)
    user.posts.create!(title: "Test")
    assert_difference("Post.count", -1) { user.destroy }
  end
end
```

### Testing Scopes

```ruby
class UserScopeTest < ActiveSupport::TestCase
  test ".active returns only active users" do
    active_user = users(:active)
    inactive_user = users(:inactive)

    result = User.active

    assert_includes result, active_user
    assert_not_includes result, inactive_user
  end
end
```

### Testing Service Objects

```ruby
class CreateOrderServiceTest < ActiveSupport::TestCase
  setup do
    @params = { email: "test@example.com" }
  end

  test "returns success with valid params" do
    result = CreateOrderService.new.call(@params)
    assert result.success?
  end

  test "creates a user with valid params" do
    assert_difference("User.count", 1) do
      CreateOrderService.new.call(@params)
    end
  end

  test "returns failure with invalid params" do
    result = CreateOrderService.new.call(email: "")
    assert result.failure?
  end
end
```

## Anti-Patterns to Avoid

1. **Testing implementation, not behavior**: Test what it does, not how
2. **Too many assertions**: Split into separate test methods
3. **Brittle tests**: Don't test exact error messages or timestamps
4. **Slow tests**: Use fixtures, mock external services
5. **Mystery guests**: Make test data explicit, not hidden in unrelated fixtures
