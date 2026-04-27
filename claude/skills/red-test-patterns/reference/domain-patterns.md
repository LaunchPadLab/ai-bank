# Testing Domain Patterns

## Core Philosophy

**Minitest is plenty. Fixtures are faster.** Don't overcomplicate testing with RSpec DSL and factory bloat.

### Why Minitest over RSpec:
- Plain Ruby (no DSL to learn)
- Faster test suite
- Simpler setup
- Part of Rails (no extra gem)
- Easier to debug

### Why Fixtures over Factories:
- 10-100x faster (loaded once, not built per test)
- Shared across all tests (consistency)
- Force you to think about real data
- No factory DSL to maintain
- Easier to understand (YAML, not Ruby)

### Test Pyramid:
- Few system tests (Capybara, full browser)
- Many integration tests (controller + model)
- Some unit tests (complex model logic)

## Fixture Patterns

### Basic Fixture Structure

```yaml
# test/fixtures/cards.yml
logo:
  id: d0f1c2e3-4b5a-6789-0123-456789abcdef
  account: 37s
  board: projects
  column: backlog
  creator: david
  title: "Design new logo"
  body: "Need a fresh logo for the homepage"
  status: published
  position: 1
  created_at: <%= 2.days.ago %>
  updated_at: <%= 1.day.ago %>

shipping:
  account: 37s
  board: projects
  column: in_progress
  creator: jason
  title: "Shipping feature"
  body: "Implement shipping calculations"
  status: published
  position: 2
  created_at: <%= 3.days.ago %>

draft_card:
  account: 37s
  board: projects
  column: backlog
  creator: david
  title: "Draft card"
  status: draft
  position: 3
```

### Fixture Associations

```yaml
# test/fixtures/users.yml
david:
  identity: david
  account: 37s
  full_name: "David Heinemeier Hansson"
  timezone: "America/Chicago"

jason:
  identity: jason
  account: 37s
  full_name: "Jason Fried"
  timezone: "America/Chicago"

# test/fixtures/identities.yml
david:
  email_address: "david@myapp.com"
  password_digest: <%= BCrypt::Password.create('password', cost: 4) %>

jason:
  email_address: "jason@myapp.com"
  password_digest: <%= BCrypt::Password.create('password', cost: 4) %>

# test/fixtures/accounts.yml
37s:
  name: "myapp"
  timezone: "America/Chicago"
```

### ERB in Fixtures

```yaml
# Dynamic dates
recent_card:
  created_at: <%= 1.hour.ago %>
  updated_at: <%= 30.minutes.ago %>

# Calculations
expensive_item:
  price: <%= 100 * 1.5 %>

# Conditional data
<% if ENV['FULL_FIXTURES'] %>
extra_card:
  title: "Extra fixture"
<% end %>
```

### Fixture Inheritance (YAML Anchors)

```yaml
card_defaults: &card_defaults
  account: 37s
  board: projects
  creator: david
  status: published

card_one:
  <<: *card_defaults
  title: "Card One"
  position: 1

card_two:
  <<: *card_defaults
  title: "Card Two"
  position: 2
```

### Fixture Best Practices

**1. Name fixtures by what they represent:**
```yaml
# Good
active_card:
closed_card:
golden_card:

# Bad
card_1:
card_2:
card_3:
```

**2. Use associations by name:**
```yaml
# Good
logo:
  creator: david
  board: projects

# Bad
logo:
  creator_id: 1
  board_id: 1
```

**3. Create realistic data:**
```yaml
# Good
david:
  full_name: "David Heinemeier Hansson"
  email_address: "david@myapp.com"

# Bad
user_1:
  full_name: "Test User"
  email_address: "test@test.com"
```

**4. Keep fixtures minimal:**
```yaml
logo:
  title: "Design new logo"
  creator: david
  board: projects
  # Rails will set timestamps, IDs, etc.
```

## Model Test Patterns

### Basic Model Test Structure

```ruby
# test/models/card_test.rb
require "test_helper"

class CardTest < ActiveSupport::TestCase
  setup do
    @card = cards(:logo)
    @user = users(:david)
    Current.user = @user
    Current.account = @card.account
  end

  teardown do
    Current.reset
  end

  test "fixtures are valid" do
    assert @card.valid?
  end

  test "requires title" do
    @card.title = nil

    assert_not @card.valid?
    assert @card.errors.added?(:title, :blank)
  end

  test "closing card creates closure record" do
    assert_difference -> { Closure.count }, 1 do
      @card.close(user: @user)
    end

    assert @card.closed?
    assert_equal @user, @card.closed_by
    assert_instance_of Time, @card.closed_at
  end

  test "reopening card destroys closure" do
    @card.close(user: @user)

    assert_difference -> { Closure.count }, -1 do
      @card.reopen
    end

    assert @card.open?
    assert_nil @card.closure
  end
end
```

### Testing Associations

```ruby
test "belongs to board" do
  assert_instance_of Board, @card.board
  assert_equal boards(:projects), @card.board
end

test "has many comments" do
  assert_respond_to @card, :comments
  assert @card.comments.count > 0
end

test "destroys dependent comments" do
  comment_ids = @card.comments.pluck(:id)

  @card.destroy!

  comment_ids.each do |id|
    assert_nil Comment.find_by(id: id)
  end
end

test "touches board on update" do
  original_time = @card.board.updated_at

  travel 1.second do
    @card.update!(title: "New title")
  end

  assert_operator @card.board.updated_at, :>, original_time
end
```

### Testing Scopes

```ruby
test "recent scope orders by created_at desc" do
  recent = Card.recent.first
  oldest = Card.recent.last

  assert_operator recent.created_at, :>=, oldest.created_at
end

test "assigned_to scope finds user's cards" do
  card = cards(:logo)
  card.assign(@user)

  assert_includes Card.assigned_to(@user), card
end

test "open scope excludes closed cards" do
  @card.close

  assert_not_includes Card.open, @card
  assert_includes Card.closed, @card
end

test "active scope excludes closed and postponed" do
  @card.close
  refute_includes Card.active, @card

  @card.reopen
  assert_includes Card.active, @card

  @card.postpone
  refute_includes Card.active, @card
end
```

### Testing Validations

```ruby
test "validates email format" do
  identity = identities(:david)

  identity.email_address = "invalid"
  assert_not identity.valid?

  identity.email_address = "valid@example.com"
  assert identity.valid?
end

test "validates uniqueness scoped to account" do
  card = Card.new(
    title: cards(:logo).title,
    board: boards(:projects),
    column: columns(:backlog),
    account: accounts(:37s)
  )

  assert card.valid?
end
```

### Testing Callbacks

```ruby
test "broadcasts creation after commit" do
  assert_broadcasts(@card.board, :cards) do
    Card.create!(
      title: "New card",
      board: @card.board,
      column: @card.column,
      account: @card.account
    )
  end
end

test "tracks event after create" do
  card = nil

  assert_difference -> { Event.count }, 1 do
    card = Card.create!(
      title: "New card",
      board: @card.board,
      column: @card.column,
      account: @card.account
    )
  end

  event = card.events.last
  assert_equal "card_created", event.action
end
```

### Testing Enums

```ruby
test "status enum" do
  @card.status_draft!
  assert @card.status_draft?

  @card.status_published!
  assert @card.status_published?

  assert_includes Card.status_published, @card
end
```

## Controller Test Patterns

### Integration Test Structure

```ruby
# test/controllers/cards_controller_test.rb
require "test_helper"

class CardsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @card = cards(:logo)
    @user = users(:david)
    sign_in_as @user
  end

  test "should get index" do
    get board_cards_path(@card.board)

    assert_response :success
    assert_select "h1", "Cards"
  end

  test "should show card" do
    get card_path(@card)

    assert_response :success
    assert_select "h1", @card.title
  end

  test "should create card" do
    assert_difference -> { Card.count }, 1 do
      post board_cards_path(@card.board), params: {
        card: {
          title: "New card",
          body: "Card body",
          column_id: @card.column_id
        }
      }
    end

    assert_redirected_to card_path(Card.last)
    assert_equal "Card created", flash[:notice]
  end

  test "should update card" do
    patch card_path(@card), params: {
      card: { title: "Updated title" }
    }

    assert_redirected_to card_path(@card)
    assert_equal "Updated title", @card.reload.title
  end

  test "should destroy card" do
    assert_difference -> { Card.count }, -1 do
      delete card_path(@card)
    end

    assert_redirected_to board_path(@card.board)
  end
end
```

### Testing Turbo Stream Responses

```ruby
test "create returns turbo stream" do
  post card_comments_path(@card),
    params: { comment: { body: "Great work!" } },
    as: :turbo_stream

  assert_response :success
  assert_equal "text/vnd.turbo-stream.html", response.media_type
  assert_match /turbo-stream/, response.body
  assert_match /comments/, response.body
end

test "destroy returns turbo stream" do
  comment = @card.comments.first

  delete card_comment_path(@card, comment),
    as: :turbo_stream

  assert_response :success
  assert_match /turbo-stream action="remove"/, response.body
end
```

### Testing Authentication and Authorization

```ruby
test "requires authentication" do
  sign_out

  get card_path(@card)

  assert_redirected_to new_session_path
end

test "requires permission to delete" do
  other_user = users(:jason)
  sign_in_as other_user

  delete card_path(@card)

  assert_response :forbidden
end

test "admin can delete any card" do
  admin = users(:admin)
  sign_in_as admin

  assert_difference -> { Card.count }, -1 do
    delete card_path(@card)
  end
end
```

### Testing JSON API Responses

```ruby
test "returns JSON for API requests" do
  get api_card_path(@card), as: :json

  assert_response :success

  json = JSON.parse(response.body)
  assert_equal @card.title, json["title"]
  assert_equal @card.id, json["id"]
end

test "creates via JSON API" do
  assert_difference -> { Card.count }, 1 do
    post api_cards_path, params: {
      card: { title: "API card" }
    }, as: :json
  end

  assert_response :created
end
```

### Testing Filters and Scoping

```ruby
test "filters by status" do
  get cards_path, params: { filter: { status: "draft" } }

  assert_response :success
  assert_select ".card", count: Card.status_draft.count
end

test "scopes to current account" do
  other_account_card = cards(:other_account_card)

  get cards_path

  assert_response :success
  assert_select "##{dom_id(@card)}"
  assert_select "##{dom_id(other_account_card)}", count: 0
end
```

## System Test Patterns

### Basic System Test

```ruby
# test/system/cards_test.rb
require "application_system_test_case"

class CardsSystemTest < ApplicationSystemTestCase
  setup do
    @card = cards(:logo)
    @user = users(:david)
    sign_in_as @user
  end

  test "creating a card" do
    visit board_path(@card.board)

    click_link "New Card"

    fill_in "Title", with: "System test card"
    fill_in "Body", with: "Created from system test"
    click_button "Create Card"

    assert_text "Card created"
    assert_text "System test card"
  end

  test "editing a card" do
    visit card_path(@card)

    click_link "Edit"
    fill_in "Title", with: "Updated title"
    click_button "Update Card"

    assert_text "Updated title"
  end
end
```

### Testing Turbo Streams in System Tests

```ruby
test "adding a comment with Turbo Streams" do
  visit card_path(@card)

  fill_in "Body", with: "Great work!"
  click_button "Add Comment"

  assert_text "Great work!"
  assert_selector ".comment", text: "Great work!"
end

test "real-time updates" do
  visit card_path(@card)

  using_session(:other_user) do
    sign_in_as users(:jason)
    visit card_path(@card)

    fill_in "Body", with: "From another user"
    click_button "Add Comment"
  end

  assert_text "From another user"
end
```

### Testing JavaScript Interactions

```ruby
test "toggling card details" do
  visit card_path(@card)

  assert_no_selector ".card__details--expanded"

  click_button "Show Details"

  assert_selector ".card__details--expanded"

  click_button "Hide Details"

  assert_no_selector ".card__details--expanded"
end

test "filtering cards" do
  visit cards_path

  assert_selector ".card", count: Card.count

  fill_in "Search", with: @card.title

  assert_selector ".card", count: 1
  assert_text @card.title
end
```

### Testing Drag and Drop

```ruby
test "reordering cards" do
  visit board_path(@card.board)

  first_card = find(".card:first-child")
  second_card = find(".card:nth-child(2)")

  first_card.drag_to(second_card)

  within ".card:first-child" do
    assert_text second_card.text
  end
end
```

## Job Test Patterns

```ruby
# test/jobs/notify_recipients_job_test.rb
require "test_helper"

class NotifyRecipientsJobTest < ActiveJob::TestCase
  test "enqueues job" do
    comment = comments(:logo_comment)

    assert_enqueued_with job: NotifyRecipientsJob, args: [comment] do
      NotifyRecipientsJob.perform_later(comment)
    end
  end

  test "creates notifications for recipients" do
    comment = comments(:logo_comment)

    assert_difference -> { Notification.count }, 2 do
      NotifyRecipientsJob.perform_now(comment)
    end
  end

  test "doesn't notify comment creator" do
    comment = comments(:logo_comment)
    creator_id = comment.creator_id

    NotifyRecipientsJob.perform_now(comment)

    refute Notification.exists?(recipient_id: creator_id, notifiable: comment)
  end
end
```

## Mailer Test Patterns

```ruby
# test/mailers/magic_link_mailer_test.rb
require "test_helper"

class MagicLinkMailerTest < ActionMailer::TestCase
  test "sign in instructions" do
    magic_link = magic_links(:david_sign_in)
    email = MagicLinkMailer.sign_in_instructions(magic_link)

    assert_emails 1 do
      email.deliver_now
    end

    assert_equal ["david@myapp.com"], email.to
    assert_equal "Sign in to Fizzy", email.subject
    assert_match magic_link.code, email.body.to_s
    assert_match session_magic_link_url(code: magic_link.code), email.body.to_s
  end
end
```

## Test Helper Patterns

### Sign In Helper

```ruby
# test/test_helper.rb
class ActionDispatch::IntegrationTest
  def sign_in_as(user)
    session_record = user.identity.sessions.create!
    cookies.signed[:session_token] = session_record.token

    Current.user = user
    Current.identity = user.identity
    Current.session = session_record
  end

  def sign_out
    cookies.delete(:session_token)
    Current.reset
  end
end
```

### Custom Assertions

```ruby
# test/test_helper.rb
class ActiveSupport::TestCase
  def assert_broadcasts(stream, target = nil, &block)
    # Custom assertion for Turbo Stream broadcasts
  end

  def assert_enqueued_email(mailer, method, args: nil, &block)
    assert_enqueued_with(
      job: ActionMailer::MailDeliveryJob,
      args: [mailer.to_s, method.to_s, "deliver_now", { args: args }],
      &block
    )
  end
end
```

### Fixture Helper Methods

```ruby
# test/test_helper.rb
class ActiveSupport::TestCase
  fixtures :all

  def reload_fixtures
    ActiveRecord::FixtureSet.reset_cache
    ActiveRecord::FixtureSet.create_fixtures(
      "test/fixtures",
      ActiveRecord::FixtureSet.fixture_table_names
    )
  end
end
```

## Testing Concerns

```ruby
# test/models/concerns/closeable_test.rb
require "test_helper"

class CloseableTest < ActiveSupport::TestCase
  class DummyCloseable < ApplicationRecord
    self.table_name = "cards"
    include Card::Closeable
  end

  setup do
    @record = DummyCloseable.find(cards(:logo).id)
  end

  test "close creates closure record" do
    assert_difference -> { Closure.count }, 1 do
      @record.close
    end

    assert @record.closed?
  end

  test "closed scope finds closed records" do
    @record.close

    assert_includes DummyCloseable.closed, @record
  end
end
```

## Performance Testing

```ruby
# test/performance/card_query_test.rb
require "test_helper"

class CardQueryTest < ActiveSupport::TestCase
  test "active scope is efficient" do
    100.times do |i|
      Card.create!(
        title: "Card #{i}",
        board: boards(:projects),
        column: columns(:backlog),
        account: accounts(:37s)
      )
    end

    assert_queries(1) do
      Card.active.load
    end
  end

  test "n+1 query prevention" do
    assert_queries(2) do
      cards = Card.includes(:comments).limit(10)
      cards.each do |card|
        card.comments.count
      end
    end
  end
end
```

## Common Test Patterns Catalog

### 1. Assert Creates Record
```ruby
assert_difference -> { Card.count }, 1 do
  @card.close
end
```

### 2. Assert Updates Attribute
```ruby
@card.close
assert @card.closed?
assert_equal @user, @card.closed_by
```

### 3. Assert Raises Error
```ruby
assert_raises ActiveRecord::RecordInvalid do
  Card.create!(title: nil)
end
```

### 4. Assert Includes in Collection
```ruby
assert_includes Card.open, @card
refute_includes Card.closed, @card
```

### 5. Assert Redirects
```ruby
post cards_path, params: { card: { title: "Test" } }
assert_redirected_to card_path(Card.last)
```

### 6. Assert Response Code
```ruby
get card_path(@card)
assert_response :success
```

### 7. Assert Select Elements
```ruby
get cards_path
assert_select "h1", "Cards"
assert_select ".card", count: 3
```

### 8. Assert Text Present
```ruby
visit card_path(@card)
assert_text @card.title
```

### 9. Assert Job Enqueued
```ruby
assert_enqueued_with job: NotifyRecipientsJob do
  @card.close
end
```

### 10. Assert Email Sent
```ruby
assert_emails 1 do
  @identity.send_magic_link
end
```

## Parallel Testing

```ruby
# test/test_helper.rb
class ActiveSupport::TestCase
  parallelize(workers: :number_of_processors)

  parallelize_setup do |worker|
    # Setup code for each worker
  end

  parallelize_teardown do |worker|
    # Cleanup code for each worker
  end
end
```

## Coverage and CI

```ruby
# Add to test_helper.rb for coverage
if ENV['COVERAGE']
  require 'simplecov'
  SimpleCov.start 'rails' do
    add_filter '/test/'
    add_filter '/config/'

    minimum_coverage 80
  end
end
```

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: ruby/setup-ruby@v1
        with:
          bundler-cache: true
      - run: bin/rails db:setup
      - run: bin/rails test
      - run: bin/rails test:system
```

## Testing Anti-Patterns to Avoid

### Don't use factories
```ruby
# BAD
let(:card) { FactoryBot.create(:card) }

# GOOD - Use fixtures
setup do
  @card = cards(:logo)
end
```

### Don't test implementation details
```ruby
# BAD - Testing internals
test "calls create_closure" do
  @card.expects(:create_closure!)
  @card.close
end

# GOOD - Test behavior
test "closing creates closure" do
  @card.close
  assert @card.closed?
end
```

### Don't create unnecessary data in tests
```ruby
# BAD - Creating when fixtures exist
setup do
  @user = User.create!(name: "Test")
  @card = Card.create!(title: "Test", user: @user)
end

# GOOD - Use fixtures
setup do
  @user = users(:david)
  @card = cards(:logo)
end
```

### Don't test Rails functionality
```ruby
# BAD - Rails already tests this
test "validates presence of title" do
  @card.title = nil
  assert_not @card.valid?
end

# GOOD - Only test custom validations
test "validates title doesn't contain profanity" do
  @card.title = "bad word"
  assert_not @card.valid?
end
```

---

# RED Phase Domain Patterns

## TDD Philosophy - RED Phase

### The TDD Cycle

```
┌─────────────────────────────────────────────────────────┐
│  1. RED    │  Write a failing test                      │ ← YOU ARE HERE
├─────────────────────────────────────────────────────────┤
│  2. GREEN  │  Write minimum code to pass                │
├─────────────────────────────────────────────────────────┤
│  3. REFACTOR │  Improve code without breaking tests    │
└─────────────────────────────────────────────────────────┘
```

### RED Phase Rules

1. **Write the test BEFORE the code** - The test must fail because the code doesn't exist
2. **One test at a time** - Focus on one atomic behavior
3. **The test must fail for the RIGHT reason** - Not syntax error, but unsatisfied assertion
4. **Clearly name expected behavior** - The test is a specification
5. **Think API first** - How do you want to use this code?

## RED Phase Workflow

### Step 1: Understand the Requested Feature

Analyze the user's request to identify:
- The type of component to create (model, service, controller, etc.)
- Expected behaviors
- Edge cases
- Potential dependencies

### Step 2: Plan the Tests

Break down the feature into testable behaviors:
```
Feature: UserRegistrationService
├── Nominal case: successful registration
├── Validation: invalid email
├── Validation: password too short
├── Edge case: email already exists
└── Side effect: welcome email sent
```

### Step 3: Write the First Test (the simplest)

Always start with the simplest case - the basic "happy path".

### Step 4: Verify the Test Fails

Run the test to confirm it fails with the right error message.

### Step 5: Document Expected Result

Explain to the user what code must be implemented to make the test pass.

## RED Test Structure

```ruby
# test/services/user_registration_service_test.rb
require "test_helper"

class UserRegistrationServiceTest < ActiveSupport::TestCase
  # Service doesn't exist yet - this test MUST fail

  setup do
    @params = {
      email: "newuser@example.com",
      password: "SecurePass123!",
      first_name: "Marie"
    }
  end

  test "creates a new user with valid parameters" do
    assert_difference("User.count", 1) do
      UserRegistrationService.new(@params).call
    end
  end

  test "returns a success result with valid parameters" do
    result = UserRegistrationService.new(@params).call

    assert result.success?
  end

  test "returns the created user with valid parameters" do
    result = UserRegistrationService.new(@params).call

    assert_instance_of User, result.user
    assert_equal "newuser@example.com", result.user.email
  end
end
```

## Expected Output Format

When you create a RED test, provide:

1. **The complete test file** with all test cases
2. **The associated fixtures** if necessary
3. **Test execution** to prove it fails
4. **Result explanation**: why the test fails and what code must be implemented
5. **Expected code signature**: the minimal interface the developer must implement

Example output:
```
## Created Tests

I created the RED test for `UserRegistrationService`.

### File: `test/services/user_registration_service_test.rb`
[test content]

### Fixtures: `test/fixtures/users.yml` (updated)
[added fixture entries]

### Execution Result
$ bin/rails test test/services/user_registration_service_test.rb
E

Errors:
  1) UserRegistrationServiceTest#test_creates_a_new_user_with_valid_parameters
     NameError: uninitialized constant UserRegistrationService

### To make this test pass, implement:

```ruby
# app/services/user_registration_service.rb
class UserRegistrationService
  Result = Data.define(:success?, :user, :errors)

  def initialize(params)
    @params = params
  end

  def call
    # Your implementation here
  end
end
```

## RED Phase Rules

### Always Do

- Write failing tests BEFORE the code
- Run each test to confirm it fails correctly
- Create necessary fixtures
- Clearly document why the test fails
- Provide expected interface of code to implement
- Cover edge cases from RED phase
- Use descriptive names for tests

### Ask Before

- Modifying existing fixtures that could impact other tests
- Adding test gems
- Modifying Minitest configuration
- Creating global shared test helpers

### Never Do

- Modify source code in `app/` - you test, you don't implement
- Write code that makes tests pass - that's the GREEN phase
- Create passing tests - in RED phase, everything must fail
- Delete or disable existing tests
- Use `skip` without valid reason
- Write tests with syntax errors (test must compile)
- Test implementation details instead of behavior

## TDD Best Practices

### Write Expressive Tests

```ruby
# BAD - Not clear about expected behavior
test "works" do
  assert UserRegistrationService.new(@params).call
end

# GOOD - Behavior is explicit
test "creates a user with the provided email" do
  result = UserRegistrationService.new(@params).call

  assert_equal "user@example.com", result.user.email
end
```

### One Concept Per Test

```ruby
# BAD - Tests multiple things
test "registers user and sends email and logs event" do
  assert_difference("User.count", 1) { service.call }
  assert_equal 1, ActionMailer::Base.deliveries.size
  assert_equal "user_registered", AuditLog.last.action
end

# GOOD - One concept per test
test "creates a new user" do
  assert_difference("User.count", 1) { service.call }
end

test "sends a welcome email" do
  assert_enqueued_email_with UserMailer, :welcome_email do
    service.call
  end
end

test "logs the registration event" do
  service.call

  assert_equal "user_registered", AuditLog.last.action
end
```

### Think API First

Before writing the test, ask yourself:
- How will I call this code?
- What parameters are necessary?
- What should the code return?
- How to handle errors?

The test defines the API before implementation.
