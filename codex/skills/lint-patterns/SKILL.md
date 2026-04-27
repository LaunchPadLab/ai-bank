---
name: "lint-patterns"
description: "RuboCop rules, ERB lint configuration, auto-correct patterns, Rails Omakase standards, and safe vs unsafe correction guidelines. Reference material for Ruby/Rails linting."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: user-invocable. -->

# Linting Patterns for Ruby on Rails

## RuboCop Commands

### Analysis and Auto-Correction

- **Fix entire project:** `bundle exec rubocop -a`
- **Aggressive auto-correct:** `bundle exec rubocop -A` (warning: riskier)
- **Specific file:** `bundle exec rubocop -a app/models/user.rb`
- **Specific directory:** `bundle exec rubocop -a app/services/`
- **Tests only:** `bundle exec rubocop -a test/`

### Analysis Without Modification

- **Analyze all:** `bundle exec rubocop`
- **Detailed format:** `bundle exec rubocop --format detailed`
- **Show violated rules:** `bundle exec rubocop --format offenses`
- **Specific file:** `bundle exec rubocop app/models/user.rb`

### Rule Management

- **Generate TODO list:** `bundle exec rubocop --auto-gen-config`
- **List active cops:** `bundle exec rubocop --show-cops`
- **Show config:** `bundle exec rubocop --show-config`

## What You CAN Fix (Safe Zone)

### Formatting and Indentation

```ruby
# BEFORE
class User<ApplicationRecord
def full_name
"#{first_name} #{last_name}"
end
end

# AFTER (fixed by you)
class User < ApplicationRecord
  def full_name
    "#{first_name} #{last_name}"
  end
end
```

### Spaces and Blank Lines

```ruby
# BEFORE
def create
  @user=User.new(user_params)


  if @user.save
    redirect_to @user
  else
    render :new,status: :unprocessable_entity
  end
end

# AFTER (fixed by you)
def create
  @user = User.new(user_params)

  if @user.save
    redirect_to @user
  else
    render :new, status: :unprocessable_entity
  end
end
```

### Naming Conventions

```ruby
# BEFORE
def GetUserData
  userID = params[:id]
  User.find(userID)
end

# AFTER (fixed by you)
def get_user_data
  user_id = params[:id]
  User.find(user_id)
end
```

### Quotes and Interpolation

```ruby
# BEFORE
name = 'John'
message = "Hello " + name

# AFTER (fixed by you)
name = "John"
message = "Hello #{name}"
```

### Modern Hash Syntax

```ruby
# BEFORE
{ :name => "John", :age => 30 }

# AFTER (fixed by you)
{ name: "John", age: 30 }
```

### Method Order in Models

```ruby
# BEFORE
class User < ApplicationRecord
  def full_name
    "#{first_name} #{last_name}"
  end

  validates :email, presence: true
  has_many :items
end

# AFTER (fixed by you)
class User < ApplicationRecord
  # Associations
  has_many :items

  # Validations
  validates :email, presence: true

  # Instance methods
  def full_name
    "#{first_name} #{last_name}"
  end
end
```

### Documentation and Comments

```ruby
# BEFORE
# TODO fix this

# AFTER (fixed by you)
# TODO: Fix this method to handle edge cases
```

## What You Should NEVER Do (Danger Zone)

### Modify Business Logic

```ruby
# DON'T TRY to fix this even if RuboCop suggests it:
if user.active? && user.premium?
  grant_access
end
```

### Change Algorithms

```ruby
# DON'T TRANSFORM automatically:
users = []
User.all.each { |u| users << u.name }

# TO:
users = User.all.map(&:name)
# Even if it's more idiomatic, this changes behavior
```

### Modify Database Queries

```ruby
# DON'T CHANGE:
User.where(active: true).select(:id, :name)
# TO:
User.where(active: true).pluck(:id, :name)
# This changes the return type (ActiveRecord vs Array)
```

### Sensitive Files to Avoid

- `config/routes.rb` – Impacts routing
- `db/schema.rb` – Auto-generated
- `config/environments/*.rb` – Critical configuration

## Workflow

### Step 1: Analyze Before Fixing

```bash
bundle exec rubocop [file_or_directory]
```

Examine reported offenses and identify those that are safe to auto-correct.

### Step 2: Apply Auto-Corrections

```bash
bundle exec rubocop -a [file_or_directory]
```

The `-a` option (auto-correct) applies only safe corrections.

### Step 3: Verify Results

```bash
bundle exec rubocop [file_or_directory]
```

Confirm no offenses remain or list those requiring manual intervention.

### Step 4: Run Tests

After each linting session, verify tests still pass:

```bash
bin/rails test
```

If tests fail, **immediately revert your changes** with `git restore` and report the issue.

### Step 5: Document Corrections

Clearly explain to the user:
- Which files were modified
- What types of corrections were applied
- If any offenses remain to be fixed manually

## RuboCop Omakase Standards

The project uses `rubocop-rails-omakase`, which implements official Rails conventions:

### General Principles

1. **Indentation:** 2 spaces (never tabs)
2. **Line length:** Maximum 120 characters (Omakase tolerance)
3. **Quotes:** Double quotes by default `"string"`
4. **Hash:** Modern syntax `key: value`
5. **Parentheses:** Required for methods with arguments

### Rails Code Organization

**Models (standard order):**
```ruby
class User < ApplicationRecord
  # Includes and extensions
  include Searchable

  # Constants
  ROLES = %w[admin user guest].freeze

  # Enums
  enum :status, { active: 0, inactive: 1 }

  # Associations
  belongs_to :organization
  has_many :items

  # Validations
  validates :email, presence: true
  validates :name, length: { minimum: 2 }

  # Callbacks
  before_save :normalize_email

  # Scopes
  scope :active, -> { where(status: :active) }

  # Class methods
  def self.find_by_email(email)
    # ...
  end

  # Instance methods
  def full_name
    # ...
  end

  private

  # Private methods
  def normalize_email
    # ...
  end
end
```

**Controllers:**
```ruby
class UsersController < ApplicationController
  before_action :authenticate_user!
  before_action :set_user, only: %i[show edit update destroy]

  def index
    @users = User.all
  end

  private

  def set_user
    @user = User.find(params[:id])
  end

  def user_params
    params.expect(user: [ :name, :email ])
  end
end
```

## Exception Handling

### When to Disable RuboCop

Sometimes a rule must be ignored for a good reason:

```ruby
# rubocop:disable Style/GuardClause
def complex_method
  if condition
    # Complex code where a guard clause doesn't improve readability
  end
end
# rubocop:enable Style/GuardClause
```

**NEVER add a `rubocop:disable` directive without user approval.**

### Report Uncorrectable Issues

If RuboCop reports offenses you cannot auto-correct:

> "I formatted the code with `bundle exec rubocop -a`, but X offenses remain that require manual intervention:
>
> - `Style/ClassLength`: The `DataProcessingService` class exceeds 100 lines (refactoring recommended)
> - `Metrics/CyclomaticComplexity`: The `calculate` method is too complex (simplification needed)
>
> These corrections touch business logic and are outside my scope."

## Commands to NEVER Use

- **`rubocop --auto-gen-config`** without explicit permission (changes linting policy)
- **Manual modifications to `.rubocop.yml`** without permission (impacts team standards)
- **`rubocop -A` (auto-correct-all)** on critical files (applies potentially dangerous corrections; only use `-a` for safe auto-correct)

## Typical Use Cases

### Case 1: Lint a New File
```bash
bundle exec rubocop -a app/services/new_service.rb
```

### Case 2: Clean Tests After Modifications
```bash
bundle exec rubocop -a test/
```

### Case 3: Prepare a Commit
```bash
bundle exec rubocop
bundle exec rubocop -a
```

### Case 4: Lint a Specific Directory
```bash
bundle exec rubocop -a app/models/
bundle exec rubocop -a app/controllers/
```

## Agent Verification

- Prefer safe autocorrect with `bundle exec rubocop -a path/to/file`.
- Re-run `bundle exec rubocop path/to/file` after autocorrect to verify no offenses remain.
- Do not run unsafe autocorrect (`rubocop -A`) or change lint configuration without explicit user approval.
