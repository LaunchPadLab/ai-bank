---
name: testing-patterns
description: Rails Minitest testing patterns for models, controllers, integration flows, system tests, jobs, mailers, fixtures, time helpers, stubs, and focused verification commands. Use when writing or improving tests, choosing test types, debugging flaky tests, or replacing brittle assertions.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Rails Testing Patterns

Use this skill when the task is primarily about test structure, test coverage, or verification. Use `red-test-patterns` for the initial failing-test templates in a TDD cycle, and use `refactoring-patterns` for behavior-preserving code cleanup after tests are green.

## Choose the Test Type

| Need | Test Type | Location |
| --- | --- | --- |
| Validations, scopes, model methods | Model test | `test/models/` |
| Plain Ruby objects and services | Unit test | `test/services/`, `test/lib/` |
| HTTP request/response behavior | Integration test | `test/controllers/` or `test/integration/` by repo convention |
| Full browser flow with JS | System test | `test/system/` |
| Background execution | Job test | `test/jobs/` |
| Email rendering/delivery | Mailer test | `test/mailers/` |
| ViewComponent rendering | Component test | `test/components/` |
| Authorization rules | Policy test | `test/policies/` |

Prefer the narrowest test that proves the behavior. Add a broader integration or system test when the risk is in wiring, routing, Turbo behavior, JavaScript, or user-visible workflow.

## Model Tests

```ruby
require "test_helper"

class MembershipTest < ActiveSupport::TestCase
  test "requires account" do
    membership = memberships(:active)
    membership.account = nil

    assert_not membership.valid?
    assert membership.errors.added?(:account, :blank)
  end

  test ".active returns active memberships" do
    assert_includes Membership.active, memberships(:active)
    assert_not_includes Membership.active, memberships(:inactive)
  end
end
```

Use `errors.added?(:field, :error)` for validation internals. Assert exact English messages only when testing user-facing copy.

## Integration Tests

```ruby
class BoardsTest < ActionDispatch::IntegrationTest
  setup do
    sign_in_as users(:owner)
    @account = accounts(:acme)
  end

  test "creates board" do
    assert_difference -> { @account.boards.count }, 1 do
      post account_boards_path(@account), params: {
        board: { name: "Launch" }
      }
    end

    assert_redirected_to account_board_path(@account, @account.boards.last)
  end
end
```

Follow the repo's convention for `test/controllers/` vs `test/integration/`. Modern Rails integration tests use `ActionDispatch::IntegrationTest` either way.

## System Tests

```ruby
class BoardFlowTest < ApplicationSystemTestCase
  test "user creates a board" do
    sign_in_as users(:owner)
    visit account_boards_path(accounts(:acme))

    click_on "New board"
    fill_in "Name", with: "Launch"
    click_on "Create board"

    assert_text "Board was successfully created"
    assert_text "Launch"
  end
end
```

Use system tests for browser-only risk: Turbo Frames/Streams, Stimulus controllers, modals, file uploads, and multi-step flows.

## Job Tests

For Active Job:

```ruby
class ReminderJobTest < ActiveJob::TestCase
  test "enqueues reminder email" do
    user = users(:one)

    assert_enqueued_email_with UserMailer, :reminder, args: [user] do
      ReminderJob.perform_later(user)
    end
  end
end
```

For native Sidekiq jobs, use Sidekiq's testing helpers instead of Active Job assertions.

## Mailer Tests

```ruby
class UserMailerTest < ActionMailer::TestCase
  test "welcome" do
    email = UserMailer.welcome(users(:one))

    assert_emails 1 do
      email.deliver_now
    end

    assert_equal ["user@example.com"], email.to
    assert_match "Welcome", email.subject
  end
end
```

## Fixtures

Keep fixtures small and named by role:

```yaml
owner:
  email_address: owner@example.com

member:
  email_address: member@example.com
```

Prefer explicit fixture names (`owner`, `admin_membership`, `archived_board`) over generic names (`one`, `two`) when the role matters to the test.

## Time Helpers

```ruby
test "expires after deadline" do
  travel_to 2.days.from_now do
    assert orders(:pending).expired?
  end
end
```

Use `travel_to` for time-sensitive behavior and avoid `sleep`.

## Stubs

```ruby
PaymentGateway.stub :charge, PaymentGateway::Result.success do
  assert_difference "Payment.count", 1 do
    Payments::Create.call(order: orders(:one))
  end
end
```

Stub only external boundaries or expensive collaborators. Avoid stubbing the object under test.

## Agent Verification

- Run the focused test first, for example `bin/rails test test/models/membership_test.rb`.
- Run the smallest integration/system test that covers changed wiring.
- For broad shared behavior, run the affected directory and then `bin/rails test`.
- Run lint checks if test files or helper style changed.
