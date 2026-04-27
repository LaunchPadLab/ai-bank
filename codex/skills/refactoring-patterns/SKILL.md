---
name: "refactoring-patterns"
description: "Refactoring recipes, anti-pattern detection, and codebase modernization patterns for Rails. Reference material for systematic refactoring."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: user-invocable. -->

# Refactoring Patterns

## Philosophy: Incremental Refactoring, Not Big Rewrites

```ruby
# ❌ BAD: Big rewrite all at once
def refactor_codebase
  # Delete everything → Rebuild from scratch → Break everything in production
end

# ✅ GOOD: Incremental refactoring
def refactor_codebase
  # 1. Add tests for existing behavior
  # 2. Make small, safe changes
  # 3. Run tests after each change
  # 4. Deploy incrementally
  # 5. Keep both old and new code during transition
end
```

## Specialized Agents for Refactoring

| Agent | Refactoring Use |
|---|---|
| @crud-agent | Custom actions → RESTful resources; god controllers → focused controllers |
| @concerns-agent | Duplicate code → shared concerns; fat models → models + concerns |
| @model-agent | Service objects → model methods; anemic models → rich domain models |
| @state-records-agent | Booleans / timestamps / enums → polymorphic state records |
| @auth-agent | Devise → custom passwordless auth; OAuth → magic links |
| @turbo-agent | React/Vue → Turbo Frames; AJAX → Turbo Streams; SPA → server-rendered |
| @stimulus-agent | jQuery spaghetti → Stimulus; large JS files → focused controllers |
| @test-agent | RSpec → Minitest; FactoryBot → fixtures |
| @migration-agent | Integer IDs → UUIDs; tenant foreign keys → indexed soft account references |
| @jobs-agent | Inline processing → Sidekiq background jobs |
| @events-agent | Callback hell → domain events; observer pattern → event records |
| @caching-agent | Slow caching → optimized Redis caching; manual invalidation → `touch: true` |
| @multi-tenant-agent | Single-tenant → multi-tenant; Apartment → account_id |
| @api-agent | GraphQL → REST; ActiveModel::Serializers → Jbuilder |
| @mailer-agent | Individual emails → bundled digests |

## Refactoring Workflow Patterns

### Pattern 1: Remove Service Objects

**Scenario:** App has 50+ service objects that should be model methods.

**Before → After:**
```ruby
# ❌ Anti-pattern
class ProjectCreationService
  def initialize(user, params)
    @user = user
    @params = params
  end

  def call
    project = Project.create!(@params)
    project.add_member(@user, role: :owner)
    project.create_default_boards
    ProjectMailer.created(project).deliver_later
    project
  end
end

# ✅ Target
class Project < ApplicationRecord
  def self.create_with_defaults(creator:, **attributes)
    transaction do
      project = create!(attributes.merge(creator: creator))
      project.add_member(creator, role: :owner)
      project.create_default_boards
      project
    end
  end

  after_create_commit :send_creation_email

  private

  def send_creation_email
    ProjectMailer.created(self).deliver_later
  end
end
```

**Steps:**
1. @test-agent: Add tests for existing service object behavior
2. @model-agent: Move business logic to model methods
3. @test-agent: Update tests to call model methods
4. @crud-agent: Update controllers to use model methods
5. Delete service object files
6. @test-agent: Run full test suite

---

### Pattern 2: Convert Booleans to State Records

**Scenario:** Models have many boolean flags that should be state records.

**Before → After:**
```ruby
# ❌ Anti-pattern
class Project < ApplicationRecord
  # archived, boolean
  # published, boolean
  # locked, boolean
  # approved, boolean
end

# ✅ Target
class Project < ApplicationRecord
  has_one :archival, dependent: :destroy
  has_one :publication, dependent: :destroy
  has_one :closure, dependent: :destroy
  has_one :approval, dependent: :destroy

  def archived?
    archival.present?
  end
end
```

**Steps:**
1. @migration-agent: Create state record tables (archivals, publications, etc.)
2. @state-records-agent: Create state record models
3. @migration-agent: Backfill state records from boolean columns
4. @model-agent: Update model associations and methods
5. @crud-agent: Create state record controllers
6. @test-agent: Update tests to use state records
7. @migration-agent: Remove boolean columns (after transition)

---

### Pattern 3: Replace Devise with Custom Auth

**Scenario:** App uses Devise with 20+ files and complexity.

**Before → After:**
```ruby
# ❌ Anti-pattern
# config/initializers/devise.rb (100+ lines)
# 20+ Devise views
# Multiple authentication strategies

# ✅ Target
# app/models/user.rb (~30 lines)
# app/models/magic_link.rb (~20 lines)
# app/controllers/sessions_controller.rb (~30 lines)
# 3 simple views
```

**Steps:**
1. @test-agent: Document existing authentication behavior with tests
2. @auth-agent: Implement custom passwordless auth alongside Devise
3. @migration-agent: Create magic_links table
4. @test-agent: Test new auth system in isolation
5. @crud-agent: Add feature flag to switch between auth systems
6. Deploy and test in production with flag
7. Remove Devise after successful migration

---

### Pattern 4: Convert React SPA to Turbo

**Scenario:** App has React frontend that should be server-rendered with Turbo.

**Before → After:**
```ruby
# ❌ Anti-pattern
# Frontend: React app with 50+ components
# Backend: Rails API only
# State management: Redux
# Build: Webpack, Babel, complex tooling

# ✅ Target
# Frontend: ERB templates with Turbo Frames
# Backend: Rails controllers with HTML + JSON
# State: Server-side in database
# Build: Importmap, no Node.js
```

**Steps:**
1. @crud-agent: Add HTML responses to API controllers (respond_to)
2. @turbo-agent: Create Turbo Frame versions of React components
3. @stimulus-agent: Add Stimulus for client-side interactions
4. @test-agent: Add system tests for Turbo version
5. Feature flag to switch between React and Turbo
6. Gradually migrate page by page
7. Remove React after full migration

---

### Pattern 5: Add Multi-Tenancy

**Scenario:** Single-tenant app needs to support multiple accounts.

**Before → After:**
```ruby
# ❌ Single-tenant
class Board < ApplicationRecord
  belongs_to :user
end

# ✅ Multi-tenant
class Board < ApplicationRecord
  belongs_to :account
  belongs_to :creator, class_name: "User"
end
```

**Steps:**
1. @multi-tenant-agent: Create Account and Membership models
2. @migration-agent: Add indexed `account_id` UUID columns to all tenant-scoped tables without database foreign keys unless explicitly approved
3. @migration-agent: Backfill account_id from existing data
4. @model-agent: Add account associations to all models
5. @crud-agent: Update controllers for account scoping
6. @test-agent: Update all tests for multi-tenancy
7. @auth-agent: Update authentication for account context

---

### Pattern 6: RSpec to Minitest Migration

**Scenario:** App has 2000+ RSpec tests that should be Minitest.

**Before → After:**
```ruby
# ❌ RSpec
RSpec.describe Project do
  let(:user) { create(:user) }
  let(:project) { create(:project, creator: user) }

  describe "#archive" do
    it "sets archived_at" do
      project.archive
      expect(project.archived_at).to be_present
    end
  end
end

# ✅ Minitest
class ProjectTest < ActiveSupport::TestCase
  test "archive sets archived_at" do
    project = projects(:one)
    project.archive
    assert project.archived_at.present?
  end
end
```

**Steps:**
1. @test-agent: Create fixtures from factory definitions
2. @test-agent: Convert one test file to Minitest as example
3. @test-agent: Create conversion script for remaining tests
4. Run both RSpec and Minitest in parallel during transition
5. @test-agent: Verify all tests pass in Minitest
6. Remove RSpec after full migration

---

### Pattern 7: Simplify Complex API

**Scenario:** App has GraphQL that should be simple REST.

**Before → After:**
```ruby
# ❌ GraphQL: 50+ type files, resolvers, mutations, subscriptions

# ✅ REST: respond_to blocks, Jbuilder views, simple RESTful routes
```

**Steps:**
1. @api-agent: Add JSON format to existing controllers
2. @api-agent: Create Jbuilder templates
3. @test-agent: Add API tests for JSON responses
4. Version GraphQL as /api/v1 (deprecated)
5. Promote REST as /api/v2
6. Communicate deprecation timeline
7. Remove GraphQL after migration period

---

### Pattern 8: Extract Concerns from Fat Models

**Scenario:** Models have 500+ lines with duplicate code across models.

**Before → After:**
```ruby
# ❌ Fat model
class Project < ApplicationRecord
  # 500 lines mixing: closeable, assignable, searchable, etc.
end

class Card < ApplicationRecord
  # 400 lines with same closeable, assignable code
end

# ✅ Lean model with concerns
class Project < ApplicationRecord
  include Closeable
  include Assignable
  include Searchable
  # 100 lines of project-specific logic
end
```

**Steps:**
1. @concerns-agent: Identify duplicate patterns across models
2. @concerns-agent: Create Closeable concern
3. @test-agent: Test Closeable in isolation
4. @model-agent: Include concern in models
5. @test-agent: Verify existing tests still pass
6. Repeat for other concerns

---

### Pattern 9: Optimize Redis Infrastructure

**Scenario:** App uses Redis for caching, Sidekiq jobs, and Action Cable — optimize configuration.

**Before → After:**
```ruby
# ❌ Separate Redis instances, no connection pooling, default config

# ✅ Tuned Redis with connection pooling, namespaces, and proper config per use case
```

**Steps:**
1. @caching-agent: Configure `redis_cache_store` with connection pooling and namespaces
2. @caching-agent: Add cache warming and `touch: true` cascades
3. @turbo-agent: Verify Action Cable broadcasting via Redis adapter
4. Redis used for caching, Sidekiq, and Action Cable

---

### Pattern 10: Consolidate Mailers

**Scenario:** App sends 100 individual emails that should be bundled.

**Steps:**
1. @mailer-agent: Create digest mailer
2. @events-agent: Create notification model
3. @jobs-agent: Create digest job (runs daily)
4. @model-agent: Update models to create notifications instead of sending emails
5. @test-agent: Test digest bundling
6. Feature flag to enable digests per user
7. Remove individual emails after migration

## Common Refactoring Recipes

### God Controller → Resource Controllers

**Before:**
```ruby
class ProjectsController < ApplicationController
  def index; end
  def show; end
  def create; end
  def update; end
  def destroy; end
  def archive; end      # Should be ArchivalsController
  def publish; end      # Should be PublicationsController
  def approve; end      # Should be ApprovalsController
  def assign; end       # Should be AssignmentsController
  def comment; end      # Should be CommentsController
end
```

**After:**
```ruby
class ProjectsController < ApplicationController
  def index; end
  def show; end
  def create; end
  def update; end
  def destroy; end
end

class ArchivalsController < ApplicationController
  def create; end       # Archive project
  def destroy; end      # Unarchive project
end

class PublicationsController < ApplicationController
  def create; end
  def destroy; end
end
```

**Delegation:**
```
@crud-agent: "Extract archive action into ArchivalsController"
@crud-agent: "Extract publish action into PublicationsController"
@test-agent: "Move archive tests to archivals controller test"
```

---

### Service Object → Model Method

**Before:**
```ruby
class ProjectDuplicationService
  def initialize(project, user)
    @project = project
    @user = user
  end

  def call
    new_project = @project.dup
    new_project.creator = @user
    new_project.save!

    @project.cards.each do |card|
      new_card = card.dup
      new_card.project = new_project
      new_card.save!
    end

    new_project
  end
end
```

**After:**
```ruby
class Project < ApplicationRecord
  def duplicate_for(user)
    transaction do
      new_project = dup
      new_project.creator = user
      new_project.save!

      cards.each do |card|
        new_card = card.dup
        new_card.project = new_project
        new_card.save!
      end

      new_project
    end
  end
end
```

**Delegation:**
```
@test-agent: "Add tests for ProjectDuplicationService"
@model-agent: "Move duplication logic to Project#duplicate_for"
@crud-agent: "Update controller to call project.duplicate_for"
```

---

### Boolean → State Record

**Before:**
```ruby
class Project < ApplicationRecord
  # approved boolean
  # approved_at timestamp
  # approved_by_id integer
end

project.update(approved: true, approved_at: Time.current, approved_by: user)
if project.approved?; end
```

**After:**
```ruby
class Project < ApplicationRecord
  has_one :approval, dependent: :destroy

  def approved?
    approval.present?
  end
end

class Approval < ApplicationRecord
  belongs_to :project
  belongs_to :approver, class_name: "User"
end

project.create_approval!(approver: user)
if project.approved?; end
```

**Delegation:**
```
@migration-agent: "Create approvals table"
@state-records-agent: "Create Approval model"
@migration-agent: "Backfill approvals from approved boolean"
@model-agent: "Update Project to use approval association"
@test-agent: "Update tests to use approval record"
```

---

### AJAX → Turbo Streams

**Before:**
```javascript
$(document).on('click', '.comment-form button', function(e) {
  e.preventDefault();
  $.ajax({
    url: '/comments',
    method: 'POST',
    data: $(this).closest('form').serialize(),
    success: function(data) {
      $('.comments').append(data.html);
      $('form')[0].reset();
    }
  });
});
```

**After:**
```erb
<%# app/views/comments/create.turbo_stream.erb %>
<%= turbo_stream.append "comments", @comment %>
<%= turbo_stream.replace "comment_form", partial: "comments/form" %>

<%# Form with Turbo %>
<%= form_with model: [@card, Comment.new], id: "comment_form" do |f| %>
  <%= f.text_area :body %>
  <%= f.submit %>
<% end %>
```

**Delegation:**
```
@turbo-agent: "Convert AJAX comment form to Turbo Stream"
@stimulus-agent: "Add Stimulus controller for auto-focus"
@test-agent: "Add system test for comment creation"
```

## Refactoring Principles

### 1. Test First, Always

Before any refactoring:
1. @test-agent: Add tests for existing behavior
2. Ensure 100% test coverage for code being refactored
3. Tests should pass before refactoring starts
4. Tests should pass after each refactoring step

### 2. Incremental Changes

Never big rewrites:
1. Make smallest possible change
2. Run tests
3. Commit
4. Repeat

### 3. Feature Flags for Risky Changes

For major refactorings:
1. Implement new code alongside old code
2. Add feature flag to switch between implementations
3. Test in production with flag
4. Gradually roll out
5. Remove old code after successful migration

### 4. Backward Compatibility

During transitions:
1. Support both old and new interfaces
2. Deprecate old interface with warnings
3. Provide migration guide
4. Remove old interface after grace period

### 5. Data Migrations

For database changes:
1. @migration-agent: Add new column/table
2. @migration-agent: Backfill data
3. @model-agent: Update models to use new structure
4. @test-agent: Verify data integrity
5. @migration-agent: Remove old column/table (separate deploy)

## Decision Matrix

### When to Refactor vs. Rewrite

**Refactor incrementally when:**
- App is in production with users
- Core functionality works
- Team needs to maintain velocity
- Can deploy changes gradually

**Consider rewrite when:**
- App is a prototype/MVP
- Tech debt is overwhelming
- No tests exist
- Architecture is fundamentally wrong
- Use implement-agent to build new

### What to Refactor First

**High Priority:**
1. Remove unnecessary external dependencies (GraphQL, etc.)
2. Security issues (SQL injection, N+1 queries)
3. Performance bottlenecks
4. Code causing most bugs

**Medium Priority:**
1. Service objects to model methods
2. Booleans to state records
3. Complex JavaScript to Turbo/Stimulus
4. RSpec to Minitest

**Low Priority:**
1. Naming conventions
2. File organization
3. Comment improvements
4. Cosmetic changes

## Example: Complete Refactoring Plan

**User Request:** "Our app uses Devise, service objects, RSpec, and has fat controllers."

### Phase 1: Foundation (Week 1-2)
1. **@test-agent**: Audit test coverage, ensure 90%+
2. **@migration-agent**: Add UUIDs to primary keys (parallel with integers)
3. **@concerns-agent**: Extract shared model behavior into concerns
4. **@test-agent**: Add missing controller tests

### Phase 2: Authentication (Week 3-4)
1. **@auth-agent**: Implement custom passwordless auth alongside Devise
2. **@migration-agent**: Create magic_links table
3. **@test-agent**: Test new auth system comprehensively
4. **@crud-agent**: Add feature flag for auth system selection
5. Deploy and test with 10% of users → increase to 100%
6. Remove Devise gem and files

### Phase 3: Business Logic (Week 5-8)
1. **@test-agent**: List all service objects (estimated 20-30)
2. **@model-agent**: Refactor highest-impact service object to model method
3. **@test-agent**: Update tests for refactored service
4. **@crud-agent**: Update controllers
5. Repeat for each service object
6. **@concerns-agent**: Extract shared service logic to concerns

### Phase 4: Controllers & Tests (Week 9-12)
1. **@crud-agent**: Extract custom controller actions to resources
2. **@test-agent**: Create fixtures from factories (one file per day)
3. **@test-agent**: Convert one RSpec file to Minitest per day
4. Run both test suites in parallel
5. When Minitest reaches 100% coverage, remove RSpec

### Risk Mitigation
- All changes behind feature flags
- Gradual rollout with monitoring
- Rollback plan for each phase
- Database backups before migrations
- Test coverage maintained at 90%+

## Additional Resources

- [classic-refactorings.md](reference/classic-refactorings.md) -- Extract Method, Replace Conditional with Polymorphism, Introduce Parameter Object, Named Constants, Decompose Conditional, DRY, Guard Clauses, and Extract Service examples
