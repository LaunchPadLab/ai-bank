# Context Level 3

# Feature Specification Template

> Use this template to document a new feature BEFORE developing it.
> This document will guide the AI agent (or developers) through implementation.

## Agent Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    📋 SPECIFICATION PHASE                        │
├─────────────────────────────────────────────────────────────────┤
│ 1. @feature_specification_agent → generates this document       │
│                         ↓                                        │
│ 2. @feature_reviewer_agent → review (score X/10)                │
│                         ↓                                        │
│    [If score < 7 or critical issues: revise]                    │
│                         ↓                                        │
│ 3. @feature_planner_agent → implementation plan                 │
├─────────────────────────────────────────────────────────────────┤
│                    🔴 RED PHASE (per PR)                         │
├─────────────────────────────────────────────────────────────────┤
│ 4. @tdd_red_agent → failing tests (Gherkin → Minitest)          │
├─────────────────────────────────────────────────────────────────┤
│                    🟢 GREEN PHASE (per PR)                       │
├─────────────────────────────────────────────────────────────────┤
│ 5. Specialist agents → minimal implementation                   │
│    • @model_agent, @migration_agent (database)                  │
│    • @service_agent, @form_agent (business logic)               │
│    • @policy_agent (authorization)                              │
│    • @controller_agent (endpoints)                              │
│    • @view_component_agent (UI components)                      │
│    • @tailwind_agent (styling with Tailwind CSS)                │
│    • @mailer_agent, @job_agent (async)                          │
├─────────────────────────────────────────────────────────────────┤
│                    🔵 REFACTOR PHASE (per PR)                    │
├─────────────────────────────────────────────────────────────────┤
│ 6. @tdd_refactoring_agent → improves code (tests green)         │
│                         ↓                                        │
│ 7. @lint_agent → fixes style (Rubocop)                          │
├─────────────────────────────────────────────────────────────────┤
│                    ✅ REVIEW PHASE (per PR)                      │
├─────────────────────────────────────────────────────────────────┤
│ 8. @review_agent → code quality (SOLID, patterns)               │
│                         ↓                                        │
│ 9. @security_agent → security audit (Brakeman, vulnerabilities) │
│                         ↓                                        │
│    [If issues: return to step 5 or 6]                           │
├─────────────────────────────────────────────────────────────────┤
│                    🚀 MERGE & DEPLOY                             │
├─────────────────────────────────────────────────────────────────┤
│ 10. Merge PR → integration branch                               │
│                         ↓                                        │
│     [Repeat 4-10 for each PR step]                              │
│                         ↓                                        │
│ 11. Merge feature branch → main                                 │
│                         ↓                                        │
│ 12. Deploy → production                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Summary by Phase

| Phase | Agent(s) | Objective | Validation |
|-------|----------|-----------|------------|
| **Spec** | @feature_specification_agent | Create the spec | - |
| **Review Spec** | @feature_reviewer_agent | Validate the spec | Score ≥ 7/10 |
| **Plan** | @feature_planner_agent | Plan implementation | - |
| **RED** | @tdd_red_agent | Write failing tests | Red tests |
| **GREEN** | Specialist agents | Minimal code | Green tests |
| **REFACTOR** | @tdd_refactoring_agent | Improve code | Green tests |
| **LINT** | @lint_agent | Style & formatting | Rubocop clean |
| **REVIEW** | @review_agent | Code quality | No HIGH/CRITICAL issues |
| **SECURITY** | @security_agent | Security audit | Brakeman clean |
| **MERGE** | Developer | Integrate code | CI green |

---

## 📋 General Information

**Feature name:** `[Short descriptive name]`

**Ticket/Issue:** `#[number]`

**Priority:** `[High / Medium / Low]`

**Estimate:** `[Small / Medium / Large]` or `[X days]`

---

## 🎯 Objective

**Problem to solve:**
> Describe in 2-3 sentences the business or user problem this feature solves.
> Example: "Users cannot filter restaurants by cuisine type, making search difficult when they have a specific craving."

**Value delivered:**
> What concrete benefit for the user or the business?
> Example: "Improved user experience and 15% increase in conversion rate."

**Success criteria:**
- [ ] Measurable criterion 1
- [ ] Measurable criterion 2
- [ ] Measurable criterion 3

---

## 👤 Affected Personas

Check the impacted personas:
- [ ] Visitor (unauthenticated)
- [ ] Logged-in User
- [ ] Resource Owner (Entity Owner)
- [ ] Administrator

> 📋 **For each checked persona**, document the permissions in the Policies section below.

### Authorization Matrix

| Action | Visitor | User | Owner | Admin |
|--------|---------|------|-------|-------|
| View | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| Create | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| Edit | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| Delete | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |

---

## 📝 User Stories

### Main Story
```
As a [persona],
I want to [action],
So that [benefit].
```

**Acceptance criteria:**
- [ ] Criterion 1 (measurable, verifiable by yes/no)
- [ ] Criterion 2 (measurable, verifiable by yes/no)
- [ ] Criterion 3 (measurable, verifiable by yes/no)

> ⚠️ **Note:** Criteria must be testable and avoid subjective terms like "good", "fast", "intuitive".

### Gherkin Scenarios (Acceptance Criteria)

> 📋 These scenarios will serve as the basis for acceptance tests with `@tdd_red_agent`.

```gherkin
Feature: [Feature name]

  Background:
    Given [common context]

  # Happy Path
  Scenario: [Main success scenario]
    Given [precondition]
    When [user action]
    Then [expected result]
    And [additional verification]

  # Validation
  Scenario: [Data validation]
    Given [precondition]
    When [action with invalid data]
    Then [error message displayed]
    And [data preserved in the form]

  # Authorization
  Scenario: [Access control]
    Given [unauthorized user]
    When [attempt at protected action]
    Then [redirect or error message]
```

### Secondary Stories (optional)
> If the feature is complex, list other stories with their own Gherkin scenarios.

---

## ⚠️ Edge Cases & Error Handling

> 🔴 **REQUIRED:** Document at least 3 edge cases.

### Identified Edge Cases

| # | Type | Scenario | Expected Behavior | Error Message |
|---|------|----------|-------------------|---------------|
| 1 | Invalid input | [Description] | [Behavior] | [Message] |
| 2 | Unauthorized access | [Description] | [Behavior] | [Message] |
| 3 | Empty/null state | [Description] | [Behavior] | [Message] |
| 4 | Network/system error | [Description] | [Behavior] | [Message] |
| 5 | Concurrent operation | [Description] | [Behavior] | [Message] |

### Gherkin Scenarios for Edge Cases

```gherkin
  # Edge Case: Invalid Input
  Scenario: User submits invalid data
    Given [precondition]
    When [action with invalid data]
    Then [expected behavior]
    And [specific error message]

  # Edge Case: Unauthorized Access
  Scenario: Unauthorized user attempts action
    Given I am logged in as [unauthorized persona]
    When I attempt to [protected action]
    Then I should see "[error message]"
    And I should be redirected to [destination]

  # Edge Case: Empty State
  Scenario: No data available
    Given [no data exists]
    When I visit [page]
    Then I should see "[empty state message]"
    And I should see [call to action]
```

---

## 🔄 Incremental PR Breakdown

> ⚠️ **IMPORTANT**: Never ship a large feature as a single PR.
>
> This section is **required** for any feature estimated at more than one day of development.

### Integration Branch

**Branch name:** `feature/[feature-name]`

This branch will contain the entire feature but will only be merged into `main` once all incremental PRs are validated.

### Breakdown Plan

> Break your feature into **5-10 small PRs** maximum (ideally 3-5).
> Each PR must:
> - Be under 400 lines (ideally 50-200)
> - Have a single, clear objective
> - Be functional and tested (even if the feature is incomplete)
> - Target the integration branch (not main)

#### Step 1: [Short title]
**Branch:** `feature/[name]-step-1-[description]`

**Objective:**
> Description in 1 sentence of what this PR does.
> Example: "Add migration and cuisine_type column to the restaurants table"

**Content:**
- [ ] Migration `add_cuisine_type_to_restaurants`
- [ ] Index on the column
- [ ] Migration tests (up/down)

**Estimate:** 30 min dev + 15 min review

**Tests included:**
- [ ] Reversible migration
- [ ] Index created correctly

---

#### Step 2: [Short title]
**Branch:** `feature/[name]-step-2-[description]`

**Objective:**
> Example: "Add validations and filtering scope to the Restaurant model"

**Content:**
- [ ] Constant `CUISINE_TYPES`
- [ ] `inclusion` validation on `cuisine_type`
- [ ] `by_cuisine` scope
- [ ] Model unit tests

**Estimate:** 1h dev + 30 min review

**Tests included:**
- [ ] Validation tests
- [ ] Scope tests
- [ ] Edge cases (nil, invalid value)

---

#### Step 3: [Short title]
**Branch:** `feature/[name]-step-3-[description]`

**Objective:**
> Example: "Modify the controller to accept the cuisine filter"

**Content:**
- [ ] Modification of `RestaurantsController#index`
- [ ] Adding the `cuisine` parameter to strong params
- [ ] Controller integration tests

**Estimate:** 1h dev + 30 min review

**Tests included:**
- [ ] Controller tests with/without filter
- [ ] Authorization tests if applicable

---

#### Step 4: [Short title]
**Branch:** `feature/[name]-step-4-[description]`

**Objective:**
> Example: "Add the filtering user interface"

**Content:**
- [ ] Filter form in `index.html.erb`
- [ ] Turbo Frame for dynamic reloading
- [ ] Tailwind styling

**Estimate:** 2h dev + 1h review

**Tests included:**
- [ ] Feature tests with Capybara
- [ ] JavaScript tests if complex interactions

---

#### Step 5: [Short title] (optional)
**Branch:** `feature/[name]-step-5-[description]`

**Objective:**
> Example: "End-to-end integration tests and documentation"

**Content:**
- [ ] Complete integration tests
- [ ] Updated documentation
- [ ] Updated seeds

**Estimate:** 1h dev + 30 min review

**Tests included:**
- [ ] Full user scenario
- [ ] Regression tests

---

### Merge Strategy

```bash
# 1. Create the integration branch
git checkout -b feature/[feature-name]
git push -u origin feature/[feature-name]

# 2. For each step:
git checkout feature/[feature-name]
git checkout -b feature/[name]-step-X-[description]
# ... develop ...
git commit -m "feat: step X description"
git push -u origin feature/[name]-step-X-[description]

# 3. Create a PR targeting the integration branch
gh pr create --base feature/[feature-name] \
  --title "[Step X/Y] Short description" \
  --body "Part of #[issue]. Detailed description."

# 4. Review + merge the step
# 5. Repeat for each step

# 6. Once all steps are merged:
gh pr create --base main \
  --title "Feature: [Full feature name]" \
  --body "Closes #[issue]. All incremental PRs reviewed and merged."
```

### Breakdown Checklist

- [ ] Feature is broken into **3-10 steps maximum**
- [ ] Each step is **under 400 lines**
- [ ] Each step is **self-contained and tested**
- [ ] Step order is **logical** (dependencies respected)
- [ ] Each step has a **time estimate**
- [ ] The **full plan** is documented before starting

### Breakdown Rules

#### ✅ Good Breakdown
- Migration only (step 1)
- Model + validations (step 2)
- Controller + routes (step 3)
- Views + components (step 4)
- Integration tests (step 5)

#### ❌ Bad Breakdown
- Migration + model + controller + views (too large)
- Just validations without tests (incomplete)
- Half the controller (not self-contained)
- All tests at the end (risky)

### For Coding Agents

When using a coding agent (Claude Code, GitHub Copilot, etc.):

**❌ Don't ask:**
```
"Fully implement the [name] feature"
```

**✅ Ask instead:**
```
"Implement Step 1 of the [name] feature spec: [step 1 description]"
```

Then once Step 1 is reviewed and merged:
```
"Implement Step 2 of the [name] feature spec: [step 2 description]"
```

And so on.

**Benefits:**
- 🎯 Focused context → fewer errors
- ✅ Quick review → immediate feedback
- 🔁 Easy correction → no full rewrite
- 📈 Visible progress → team confidence

---

## 🏗️ Technical Scoping

### Affected Models

#### New Models
```ruby
# If creating a new model
class NewModel < ApplicationRecord
  # Main attributes
  # - attribute_name: type (constraints)

  # Associations
  # belongs_to :xxx
  # has_many :yyy

  # Main validations
  # validates :xxx, presence: true
end
```

#### Existing Model Modifications
**Model:** `ExistingModel`

**Changes:**
- [ ] Add attribute: `new_attribute:string`
- [ ] Add relationship: `has_many :new_relation`
- [ ] New validation: `validates :xxx, ...`
- [ ] New scope: `scope :by_xxx, -> { ... }`
- [ ] New method: `def calculate_xxx`

### Validation Rules

> 🔴 **REQUIRED:** For each user-facing field, specify validation rules.

| Field | Type | Required | Validation Rules | Error Message |
|-------|------|----------|-----------------|---------------|
| `name` | string | Yes | presence, length: 2..100 | "Name is required" |
| `email` | string | Yes | format: URI::MailTo::EMAIL_REGEXP | "Invalid email format" |
| `amount` | decimal | Yes | numericality: { greater_than: 0 } | "Amount must be positive" |
| `status` | string | Yes | inclusion: { in: STATUSES } | "Invalid status" |
| `description` | text | No | length: { maximum: 1000 } | "Description too long (max 1000)" |

### Migration(s)

```ruby
# db/migrate/YYYYMMDDHHMMSS_add_feature_name.rb
class AddFeatureName < ActiveRecord::Migration[8.1]
  def change
    # Add columns
    add_column :table_name, :column_name, :type, null: false, default: value

    # Add indexes
    add_index :table_name, :column_name

    # Create table
    create_table :new_table do |t|
      t.string :name, null: false
      t.references :parent, foreign_key: true
      t.timestamps
    end
  end
end
```

**⚠️ Migration considerations:**
- [ ] Reversible migration (`up`/`down` or `change` method)
- [ ] Indexes added on key columns
- [ ] Default values defined if needed
- [ ] Foreign keys with appropriate `on_delete`

### Controllers

#### New Controllers
- `NewController` with actions: `index`, `show`, `new`, `create`, `edit`, `update`, `destroy`

#### Existing Controller Modifications
**Controller:** `ExistingController`

**Changes:**
- [ ] New action: `custom_action`
- [ ] Strong parameters modification
- [ ] Add before_action
- [ ] Business logic modification

**Strong parameters:**
```ruby
def model_params
  params.require(:model_name).permit(:attr1, :attr2, :attr3)
end
```

### Routes

```ruby
# config/routes.rb
resources :resource_name do
  # Nested routes if needed
  resources :nested_resource, only: [:index, :create, :destroy]

  # Custom routes
  member do
    post :custom_action
  end

  collection do
    get :custom_collection_action
  end
end
```

### Services (if complex logic)

**Service:** `FeatureNameService`

**Responsibility:**
> Describe in 1-2 sentences what this service does.

**Main methods:**
```ruby
class FeatureNameService
  def initialize(params)
    @params = params
  end

  def call
    # Complex business logic here
    # Returns a result or raises an exception
  end

  private

  def step_one
    # ...
  end
end
```

### Policies (Pundit)

**Policy:** `ModelPolicy`

**New rules:**
```ruby
class ModelPolicy < ApplicationPolicy
  def action_name?
    # user.admin? || record.user == user
  end
end
```

### Views & Components

#### New Views
- `app/views/resource_name/index.html.erb`
- `app/views/resource_name/show.html.erb`
- `app/views/resource_name/_form.html.erb`

#### New Components
**Component:** `FeatureNameComponent`

```ruby
class FeatureNameComponent < ViewComponent::Base
  def initialize(param:)
    @param = param
  end

  def render?
    # Display condition
  end
end
```

#### Existing View Modifications
- [ ] View to modify: `path/to/view.html.erb`
- [ ] Type of modification: [Add a link / New form / Data display]

### JavaScript (Stimulus)

#### New Stimulus Controllers
**Controller:** `feature_name_controller.js`

```javascript
import { Controller } from "@hotwire/stimulus"

export default class extends Controller {
  static targets = ["element"]
  static values = { param: String }

  connect() {
    // Initialization
  }

  action() {
    // Logic
  }
}
```

### Jobs (Background)

**Job:** `FeatureNameJob`

```ruby
class FeatureNameJob < ApplicationJob
  queue_as :default

  def perform(param)
    # Async processing
  end
end
```

**Trigger:**
- Where: `ModelName#method_name`
- When: `after_commit :enqueue_job`

---

## 🧪 Testing Strategy

### Model Tests (Minitest)

**File:** `test/models/model_name_test.rb`

**Tests to write:**
- [ ] Validations (presence, format, uniqueness, etc.)
- [ ] Associations (belongs_to, has_many, etc.)
- [ ] Scopes (verify SQL queries)
- [ ] Business methods (logic, edge cases)
- [ ] Callbacks (after_save, before_destroy, etc.)

**Test examples:**
```ruby
class ModelNameTest < ActiveSupport::TestCase
  test "requires attribute to be present" do
    model = ModelName.new(attribute: nil)
    assert_not model.valid?
    assert model.errors.added?(:attribute, :blank)
  end

  test "requires attribute to be unique" do
    existing = model_names(:one)
    duplicate = ModelName.new(attribute: existing.attribute)
    assert_not duplicate.valid?
  end

  test "#custom_method returns expected result" do
    instance = model_names(:one)
    assert_equal expected_value, instance.custom_method
  end
end
```

### Controller Tests (Integration Tests)

**File:** `test/controllers/controller_name_controller_test.rb`

**Tests to write:**
- [ ] CRUD actions (index, show, create, update, destroy)
- [ ] Authorization (logged-in user, owner, etc.)
- [ ] Redirects and flash messages
- [ ] HTTP responses (200, 302, 404, 422, etc.)

**Test examples:**
```ruby
class ResourceNameControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:one)
    @resource = resource_names(:one)
  end

  test "GET #show returns http success" do
    get resource_path(@resource)
    assert_response :success
  end

  test "POST #create with valid params creates a new resource" do
    sign_in @user

    assert_difference("ResourceName.count", 1) do
      post resources_path, params: { resource_name: { name: "New" } }
    end

    assert_redirected_to resource_path(ResourceName.last)
  end

  test "POST #create with invalid params does not create resource" do
    sign_in @user

    assert_no_difference("ResourceName.count") do
      post resources_path, params: { resource_name: { name: "" } }
    end

    assert_response :unprocessable_entity
  end
end
```

### Integration Tests (System Tests)

**File:** `test/system/feature_name_test.rb`

**Scenarios to test:**
- [ ] Complete user journey (happy path)
- [ ] Error cases (invalid form, access denied)
- [ ] JavaScript interactions (if applicable)

**Test examples:**
```ruby
class FeatureNameTest < ApplicationSystemTestCase
  setup do
    @user = users(:one)
    sign_in @user
  end

  test "user completes the feature workflow" do
    visit new_resource_path
    fill_in "Name", with: "Example"
    click_button "Create"

    assert_text "Resource created successfully"
    assert_current_path resource_path(ResourceName.last)
  end
end
```

### Component Tests

**File:** `test/components/component_name_component_test.rb`

**Tests to write:**
- [ ] Rendering with different params
- [ ] Display conditions (`render?`)
- [ ] Generated content

**Test examples:**
```ruby
class FeatureNameComponentTest < ViewComponent::TestCase
  test "renders component with param" do
    render_inline(FeatureNameComponent.new(param: "value"))
    assert_text "value"
  end

  test "does not render when condition is false" do
    component = FeatureNameComponent.new(param: nil)
    assert_not component.render?
  end
end
```

### Policy Tests

**File:** `test/policies/policy_name_test.rb`

**Tests to write:**
- [ ] Permissions by role
- [ ] Edge cases

```ruby
class ResourcePolicyTest < ActiveSupport::TestCase
  setup do
    @resource = resource_names(:one)
  end

  test "owner can update" do
    policy = ResourcePolicy.new(@resource.user, @resource)
    assert policy.update?
  end

  test "owner can destroy" do
    policy = ResourcePolicy.new(@resource.user, @resource)
    assert policy.destroy?
  end

  test "other user cannot update" do
    other_user = users(:two)
    policy = ResourcePolicy.new(other_user, @resource)
    assert_not policy.update?
  end
end
```

---

## 🔒 Security Considerations

- [ ] **Strong parameters**: all attributes are filtered
- [ ] **Pundit authorization**: all actions are protected
- [ ] **Validations**: all user inputs are validated
- [ ] **SQL injection**: use ActiveRecord, no raw SQL
- [ ] **XSS**: use Rails helpers (sanitize, escape)
- [ ] **CSRF**: tokens present on forms
- [ ] **Mass assignment**: use `permit` correctly
- [ ] **Sensitive data**: no logging or displaying secrets

---

## ⚡ Performance Considerations

- [ ] **N+1 queries**: use `includes`/`preload`/`eager_load`
- [ ] **DB indexes**: add indexes on queried columns
- [ ] **Cache**: identify data to cache
- [ ] **Background jobs**: long tasks run asynchronously
- [ ] **Pagination**: limit list results
- [ ] **Heavy queries**: optimize with `select`, `pluck`, `exists?`

---

## 📱 UI/UX Considerations

> 🔴 **REQUIRED for features with UI:** Document interactive states.

### UI/UX Checklist
- [ ] **Responsive**: design adapted for mobile/tablet/desktop
- [ ] **Accessibility**: labels, aria-labels, contrast (WCAG 2.1 AA minimum)
- [ ] **User feedback**: flash messages, loading states
- [ ] **Client-side validation**: Stimulus + HTML5 validation
- [ ] **Error handling**: clear and actionable error messages

### Interactive States (Hotwire/Turbo)

| State | Description | Implementation |
|-------|-------------|----------------|
| **Loading** | During loading | Turbo Frame with spinner, `aria-busy="true"` |
| **Success** | Action succeeded | Flash notice, Turbo Stream append/replace |
| **Error** | Action failed | Flash alert, form preserved, inline errors |
| **Empty** | No data | Explanatory message + call-to-action |
| **Disabled** | Action unavailable | Disabled button + explanatory tooltip |

### User Messages

| Context | Type | Message |
|---------|------|---------|
| Creation succeeded | success | "[Resource] created successfully" |
| Update succeeded | success | "[Resource] updated" |
| Deletion succeeded | success | "[Resource] deleted" |
| Validation error | error | "Please correct the errors below" |
| Unauthorized | error | "You are not authorized to perform this action" |
| Not found | error | "[Resource] not found" |

---

## 🚀 Deployment Plan

### Prerequisites
- [ ] Migration tested (up & down)
- [ ] Seeds updated if necessary
- [ ] Assets precompiled (if CSS/JS changes)
- [ ] Environment variables added (if necessary)

### Steps
1. Deploy the code
2. Run migrations: `rails db:migrate`
3. Restart workers if jobs were added
4. Check logs
5. Test in production

### Rollback Plan
> How to roll back if there's a problem?
```bash
# Rollback migration
rails db:rollback STEP=1

# Redeploy previous version
kamal rollback
```

---

## 📚 Documentation to Update

- [ ] `README.md`: if major feature
- [ ] `.github/project.md`: if new main functionality
- [ ] `.github/CONTRIBUTING.md`: if new conventions
- [ ] API docs: if endpoints are exposed
- [ ] User guide: if user-facing feature

---

## ✅ Final Checklist Before Merge

### Code
- [ ] Code written and functional
- [ ] Rubocop passes without errors
- [ ] No commented-out code or `binding.pry`
- [ ] Naming conventions followed

### Tests
- [ ] All tests pass
- [ ] Coverage maintained (>90%)
- [ ] Unit tests written
- [ ] Integration tests written
- [ ] Edge cases tested

### Security
- [ ] Brakeman reports no new vulnerabilities
- [ ] Bundler Audit OK
- [ ] Policies tested
- [ ] Strong parameters verified

### Documentation
- [ ] Code commented if complex logic
- [ ] README updated if necessary
- [ ] CHANGELOG.md updated

### Review
- [ ] PR created with clear description
- [ ] Screenshots/GIF if UI changes
- [ ] Reviewer assigned
- [ ] CI/CD green

---

## 💡 Notes & Questions

> Free space for noting questions, technical decisions, or specific points of attention.

**Open questions:**
-

**Technical decisions:**
-

**Points of attention:**
-

**External dependencies:**
-

---

**Creation date:** `[YYYY-MM-DD]`

**Author:** `[@username]`

**Reviewers:** `[@username1, @username2]`

**Status:** `[Draft / In Review / Ready for Dev / In Progress / Completed]`

---

## 📋 Review Criteria (@feature_reviewer_agent)

> This section summarizes the criteria that `@feature_reviewer_agent` will verify.

### MUST HAVE (Blocking if absent)
- [ ] Objective and value clearly stated
- [ ] Personas identified
- [ ] Main user story documented
- [ ] Testable acceptance criteria (verifiable by yes/no)
- [ ] Gherkin scenarios for acceptance tests
- [ ] Edge cases documented (minimum 3)
- [ ] Complete authorization matrix

### SHOULD HAVE (Recommended)
- [ ] Validation rules table
- [ ] Technical components listed
- [ ] Database changes documented
- [ ] Pundit policies specified
- [ ] Integration points identified

### IF UI (Required if UI feature)
- [ ] Loading/error/empty/success states documented
- [ ] User messages defined
- [ ] Responsive behavior specified
- [ ] Accessibility considered (WCAG 2.1 AA)

### IF Medium/Large (Required if > 1 day)
- [ ] Broken into PRs (3-10 steps)
- [ ] Each PR < 400 lines (ideally 50-200)
- [ ] Dependencies between PRs clear
- [ ] Tests included in each PR