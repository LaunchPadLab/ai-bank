# Code Review Domain Patterns

## CRUD Philosophy Violations

**Red Flag:** Custom controller actions that should be resources

```ruby
# ❌ ANTI-PATTERN
class ProjectsController < ApplicationController
  def archive
    @project.update(archived: true)
  end

  def unarchive
    @project.update(archived: false)
  end

  def approve
    @project.update(approved: true)
  end
end

# ✅ PATTERN
class ArchivalsController < ApplicationController
  def create
    @project.create_archival!
  end

  def destroy
    @project.archival.destroy!
  end
end

class ApprovalsController < ApplicationController
  def create
    @project.create_approval!(approver: Current.user)
  end
end
```

**Review Feedback:**
```
❌ Custom actions `archive`, `unarchive`, `approve` violate "everything is CRUD" principle.

Refactor to:
1. Create ArchivalsController with create/destroy actions
2. Create ApprovalsController with create action
3. Use state records pattern (Archival, Approval models)
```

## Service Object Anti-Pattern

**Red Flag:** Service objects when model methods would suffice

```ruby
# ❌ ANTI-PATTERN
class ProjectCreationService
  def initialize(user, params)
    @user = user
    @params = params
  end

  def call
    project = Project.new(@params)
    project.creator = @user
    project.save!
    NotificationMailer.project_created(project).deliver_later
    project
  end
end

# ✅ PATTERN
class Project < ApplicationRecord
  belongs_to :creator, class_name: "User", default: -> { Current.user }

  after_create_commit :notify_team

  private

  def notify_team
    NotificationMailer.project_created(self).deliver_later
  end
end
```

**Review Feedback:**
```
❌ Service object is unnecessary overhead. This logic belongs in the Project model.

Move to:
- Use default: -> { Current.user } for creator assignment
- Use after_create_commit callback for notifications
- Remove ProjectCreationService entirely

Rich domain models > Service objects
```

## Boolean Flags Instead of State Records

**Red Flag:** Boolean columns that should be state records

```ruby
# ❌ ANTI-PATTERN
class Card < ApplicationRecord
  # closed: boolean
  # closed_at: datetime
  # closed_by_id: integer

  scope :open, -> { where(closed: false) }
  scope :closed, -> { where(closed: true) }

  def close!(user)
    update!(closed: true, closed_at: Time.current, closed_by_id: user.id)
  end
end

# ✅ PATTERN
class Card < ApplicationRecord
  has_one :closure, dependent: :destroy

  scope :open, -> { where.missing(:closure) }
  scope :closed, -> { joins(:closure) }

  def close!(user)
    create_closure!(user: user)
  end

  def closed?
    closure.present?
  end
end

class Closure < ApplicationRecord
  belongs_to :card, touch: true
  belongs_to :user
  belongs_to :account, default: -> { card.account }
end
```

**Review Feedback:**
```
❌ Boolean flags `closed`, `closed_at`, `closed_by_id` should be state records.

Refactor to:
1. Create Closure model with card_id, user_id, created_at
2. Add has_one :closure to Card
3. Update scopes to use where.missing(:closure) and joins(:closure)

Benefits:
- Know exactly when card was closed (created_at)
- Who closed it (user_id)
- Easy to query open vs closed cards
- Can add metadata (reason, etc.) later
```

## Missing Multi-Tenant Scoping

**Red Flag:** Queries without account scoping in multi-tenant apps

```ruby
# ❌ ANTI-PATTERN
class ProjectsController < ApplicationController
  def index
    @projects = Project.all
  end

  def show
    @project = Project.find(params[:id])
  end
end

# ✅ PATTERN
class ProjectsController < ApplicationController
  def index
    @projects = Current.account.projects
  end

  def show
    @project = Current.account.projects.find(params[:id])
  end
end
```

**Review Feedback:**
```
❌ Missing account scoping - security vulnerability!

All queries must scope through Current.account:
- Current.account.projects (not Project.all)
- Current.account.projects.find(id) (not Project.find(id))

This prevents users from accessing other accounts' data.
Consider adding AccountScoped concern to enforce this pattern.
```

## Fat Controllers

**Red Flag:** Business logic in controllers

```ruby
# ❌ ANTI-PATTERN
class CommentsController < ApplicationController
  def create
    @comment = @card.comments.build(comment_params)
    @comment.creator = Current.user
    @comment.account = Current.account

    if @comment.body.match?(/@\w+/)
      mentions = @comment.body.scan(/@(\w+)/).flatten
      users = User.where(username: mentions)
      users.each do |user|
        NotificationMailer.mentioned(user, @comment).deliver_later
      end
    end

    @comment.save!
    redirect_to @card
  end
end

# ✅ PATTERN
class CommentsController < ApplicationController
  def create
    @comment = @card.comments.create!(comment_params)
    redirect_to @card
  end
end

class Comment < ApplicationRecord
  belongs_to :creator, class_name: "User", default: -> { Current.user }
  belongs_to :account, default: -> { card.account }

  after_create_commit :notify_mentions

  def mentioned_users
    usernames = body.scan(/@(\w+)/).flatten
    account.users.where(username: usernames)
  end

  private

  def notify_mentions
    mentioned_users.each do |user|
      NotificationMailer.mentioned(user, self).deliver_later
    end
  end
end
```

**Review Feedback:**
```
❌ Business logic in controller should move to model.

Move to Comment model:
- Mention parsing → mentioned_users method
- Default values → belongs_to default: lambdas
- Notification logic → after_create_commit callback

Controller should just orchestrate:
@card.comments.create!(comment_params)
```

## Missing Concerns for Shared Behavior

**Red Flag:** Duplicate code across models

```ruby
# ❌ ANTI-PATTERN
class Card < ApplicationRecord
  has_one :closure
  scope :open, -> { where.missing(:closure) }
  scope :closed, -> { joins(:closure) }
  def close!; create_closure!; end
  def closed?; closure.present?; end
end

class Project < ApplicationRecord
  has_one :closure
  scope :open, -> { where.missing(:closure) }
  scope :closed, -> { joins(:closure) }
  def close!; create_closure!; end
  def closed?; closure.present?; end
end

# ✅ PATTERN
module Closeable
  extend ActiveSupport::Concern

  included do
    has_one :closure, as: :closeable, dependent: :destroy

    scope :open, -> { where.missing(:closure) }
    scope :closed, -> { joins(:closure) }
  end

  def close!(user = nil)
    create_closure!(user: user)
  end

  def closed?
    closure.present?
  end
end

class Card < ApplicationRecord
  include Closeable
end

class Project < ApplicationRecord
  include Closeable
end
```

**Review Feedback:**
```
❌ Duplicate Closeable behavior across Card and Project.

Extract to concern:
1. Create app/models/concerns/closeable.rb
2. Move shared associations, scopes, methods
3. Include Closeable in both models
```

## Poor Naming Conventions

**Red Flag:** Non-RESTful or unclear names

```ruby
# ❌ ANTI-PATTERN
class Card::Archiver < ApplicationRecord  # Should be Archival
class ProjectActivator                    # Should be Activation or Publication
def process_card                          # Vague
def handle_update                         # Vague

# ✅ PATTERN
class Card::Archival < ApplicationRecord  # Noun, represents state
class Project::Publication               # Noun, represents state
def archive_with_notification            # Specific action
def broadcast_card_update                # Specific action
```

**Naming conventions:**
- State records: Closure, Archival, Publication (nouns)
- Controllers: ClosuresController (plural resource)
- Methods: close!, archive_with_notification (action verbs)

## Missing HTTP Caching

**Red Flag:** Controllers without ETags or `fresh_when`

```ruby
# ❌ ANTI-PATTERN
class ProjectsController < ApplicationController
  def show
    @project = Current.account.projects.find(params[:id])
  end
end

# ✅ PATTERN
class ProjectsController < ApplicationController
  def show
    @project = Current.account.projects.find(params[:id])
    fresh_when @project
  end
end
```

## Fragile Tests

**Red Flag:** Tests that use complex setup instead of fixtures

```ruby
# ❌ ANTI-PATTERN (RSpec with FactoryBot)
RSpec.describe Project do
  let(:account) { create(:account) }
  let(:user) { create(:user, account: account) }
  let(:board) { create(:board, account: account, creator: user) }
  let(:project) { create(:project, board: board, creator: user) }

  it "archives project" do
    project.archive!
    expect(project.archived?).to be true
  end
end

# ✅ PATTERN (Minitest with fixtures)
class ProjectTest < ActiveSupport::TestCase
  test "archives project" do
    project = projects(:active_project)
    project.archive!
    assert project.archived?
  end
end

# fixtures/projects.yml
active_project:
  account: fizzy
  board: planning
  creator: alice
  name: "Q4 Planning"
```

**Review Feedback:**
```
❌ Using FactoryBot for test data - use fixtures instead.

Benefits of fixtures:
- Loaded once, reused across tests
- Faster test suite
- Shared test data across test files
- See all test data in one place
- No complex factory definitions
```

## Missing Background Jobs

**Red Flag:** Slow operations in request cycle

```ruby
# ❌ ANTI-PATTERN
class ReportsController < ApplicationController
  def create
    @report = Report.new(report_params)
    @report.generate_data!  # Takes 30 seconds!
    @report.save!
    redirect_to @report
  end
end

# ✅ PATTERN
class ReportsController < ApplicationController
  def create
    @report = Report.create!(report_params)
    @report.generate_later
    redirect_to @report, notice: "Report is being generated..."
  end
end

class Report < ApplicationRecord
  def generate_later
    ReportGenerationJob.perform_later(self)
  end
end

class ReportGenerationJob < ApplicationJob
  def perform(report)
    report.generate_data!
  end
end
```

**Review Feedback:**
```
❌ Slow operation (30s) blocks request - use background job.

Rule: Operations >500ms should be async.
```

## Review Checklist

### Database/Models
- [ ] Tables use UUIDs (not integer IDs)
- [ ] Tenant-scoped tables have indexed account_id
- [ ] Ordinary associations use appropriate foreign keys; tenant ownership follows the account_id convention
- [ ] State is records, not booleans
- [ ] Models use rich domain logic (not service objects)
- [ ] Concerns extract shared behavior
- [ ] Associations use touch: true for cache invalidation
- [ ] Default values use lambdas (default: -> { Current.user })

### Controllers
- [ ] All actions map to CRUD verbs
- [ ] Custom actions become new resources
- [ ] Business logic in models, not controllers
- [ ] All queries scope through Current.account
- [ ] Uses fresh_when for HTTP caching
- [ ] Includes appropriate concerns (CardScoped, etc.)
- [ ] Authorization checks use model methods

### Views
- [ ] Uses Turbo Frames for isolated updates
- [ ] Uses Turbo Streams for real-time updates
- [ ] Stimulus controllers are single-purpose
- [ ] Fragment caching with cache keys
- [ ] No complex logic in views (use helpers/presenters)

### Jobs
- [ ] Uses Sidekiq for background jobs
- [ ] Follows _later convention (export_later)
- [ ] Idempotent (safe to run multiple times)
- [ ] Has corresponding _now method for testing

### Tests
- [ ] Uses Minitest (not RSpec)
- [ ] Uses fixtures (not factories)
- [ ] Tests behavior, not implementation
- [ ] Includes system tests for workflows
- [ ] All tests scope through accounts

### Security
- [ ] No secrets in code
- [ ] All queries scope to Current.account
- [ ] CSRF protection enabled
- [ ] No SQL injection vulnerabilities
- [ ] Authorization checks present

### Performance
- [ ] HTTP caching with ETags
- [ ] Fragment caching in views
- [ ] Eager loading (includes/preload)
- [ ] Proper indexes on columns
- [ ] Slow operations in background jobs

## Review Response Format

Structure feedback as:

```markdown
## Summary
[One-sentence overall assessment]

## Critical Issues ❌
[Issues that must be fixed before merging]

### 1. [Issue Category]
**File:** [path/to/file.rb]
**Line:** [123]

**Current Code:**
[problematic code]

**Issue:** [Explain the anti-pattern]

**Fix:**
[corrected code]

**Why:** [Explain the benefit]

---

## Suggestions ⚠️
[Nice-to-have improvements]

## Praise ✅
[What was done well]

## Next Steps
[Recommended follow-up actions]
```

## Common Review Scenarios

### Reviewing a New Feature

1. **Check architecture:** Does it follow CRUD philosophy? Are concerns used appropriately? Is business logic in models?
2. **Check multi-tenancy:** Tenant queries scope through Current.account? Tenant-scoped tables have account_id? Tests verify account isolation?
3. **Check performance:** HTTP caching present? Slow operations in background jobs? Proper database indexes?
4. **Check tests:** Uses Minitest and fixtures? Tests cover edge cases? System tests for workflows?

### Reviewing a Refactoring

1. **Verify improvement:** Does it reduce complexity? Does it follow modern patterns? Is it actually better?
2. **Check backward compatibility:** Are there breaking changes? Is migration path clear? Are old tests still passing?
3. **Validate extraction:** If extracting concern, is it used >2 places? Does concern have clear responsibility?

### Reviewing a Bug Fix

1. **Root cause:** Is the actual problem fixed, or just symptoms?
2. **Test coverage:** Is there a failing test first? Does test verify the fix?
3. **Similar issues:** Could this bug exist elsewhere? Should we add checks?

## Anti-Patterns Quick Reference

| Anti-Pattern | Pattern | Agent |
|---|---|---|
| Custom controller actions | New CRUD resource | @crud-agent |
| Service objects | Model methods | @model-agent |
| Boolean flags | State records | @state-records-agent |
| Fat controllers | Move logic to models | @model-agent |
| Duplicate model code | Extract to concern | @concerns-agent |
| No account scoping | Current.account.resources | @multi-tenant-agent |
| No HTTP caching | fresh_when, etag | @caching-agent |
| Inline JavaScript | Stimulus controllers | @stimulus-agent |
| AJAX requests | Turbo Streams | @turbo-agent |
| RSpec + factories | Minitest + fixtures | @test-agent |
| Inline slow operations | Background jobs | @jobs-agent |
| Integer IDs | UUIDs | @migration-agent |
