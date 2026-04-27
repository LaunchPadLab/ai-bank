---
name: rails-model-generator
description: Creates Rails models using TDD approach - test first, then migration, then model. Use when creating new models, adding model validations, defining associations, or setting up database tables.
allowed-tools: Read, Write, Edit, Bash
---

# Rails Model Generator (TDD Approach)

## Overview

This skill creates models the TDD way:
1. Define requirements (attributes, validations, associations)
2. Write model test with expected behavior (RED)
3. Create fixtures for test data
4. Generate migration
5. Implement model to pass tests (GREEN)
6. Refactor if needed

## Workflow Checklist

```
Model Creation Progress:
- [ ] Step 1: Define requirements (attributes, validations, associations)
- [ ] Step 2: Create model test (RED)
- [ ] Step 3: Create fixtures
- [ ] Step 4: Run test (should fail - no model/table)
- [ ] Step 5: Generate migration
- [ ] Step 6: Run migration
- [ ] Step 7: Create model file (empty)
- [ ] Step 8: Run test (should fail - no validations)
- [ ] Step 9: Add validations and associations
- [ ] Step 10: Run test (GREEN)
```

## Step 1: Requirements Template

Before writing code, define the model:

```markdown
## Model: [ModelName]

### Table: [table_name]

### Attributes
| Name | Type | Constraints | Default |
|------|------|-------------|---------|
| name | string | required, unique | - |
| email | string | required, unique, email format | - |
| status | integer | enum | 0 (pending) |
| organization_id | bigint | foreign key | - |

### Associations
- belongs_to :organization
- has_many :posts, dependent: :destroy
- has_one :profile, dependent: :destroy

### Validations
- name: presence, uniqueness, length(max: 100)
- email: presence, uniqueness, format(email)
- status: inclusion in enum values

### Scopes
- active: status = active
- recent: ordered by created_at desc
- by_organization(org): where organization_id = org.id

### Instance Methods
- full_name: combines first_name and last_name
- active?: checks if status is active

### Callbacks
- before_save :normalize_email
- after_create :send_welcome_email
```

## Step 2: Create Model Test

Location: `test/models/[model_name]_test.rb`

```ruby
# frozen_string_literal: true

require "test_helper"

class ModelNameTest < ActiveSupport::TestCase
  # === Associations ===
  test "belongs to organization" do
    record = model_names(:one)
    assert_instance_of Organization, record.organization
  end

  test "has many posts" do
    record = model_names(:one)
    assert_respond_to record, :posts
  end

  test "destroys dependent posts" do
    record = model_names(:one)
    record.posts.create!(title: "Test")
    assert_difference("Post.count", -1) { record.destroy }
  end

  # === Validations ===
  test "requires name" do
    record = ModelName.new(name: nil)
    assert_not record.valid?
    assert record.errors.added?(:name, :blank)
  end

  test "requires unique email (case insensitive)" do
    existing = model_names(:one)
    record = ModelName.new(email: existing.email.upcase)
    assert_not record.valid?
  end

  test "enforces max length on name" do
    record = ModelName.new(name: "a" * 101)
    assert_not record.valid?
  end

  # === Scopes ===
  test ".active returns only active records" do
    active_record = model_names(:active)
    inactive_record = model_names(:inactive)

    result = ModelName.active

    assert_includes result, active_record
    assert_not_includes result, inactive_record
  end

  # === Instance Methods ===
  test "#full_name returns combined name" do
    record = ModelName.new(first_name: "John", last_name: "Doe")
    assert_equal "John Doe", record.full_name
  end
end
```

See [templates/model_test.erb](templates/model_test.erb) for full template.

## Step 3: Create Fixtures

Location: `test/fixtures/[model_name_plural].yml`

```yaml
# test/fixtures/model_names.yml
one:
  name: "Test Name"
  email: "user1@example.com"
  status: 0
  organization: one

active:
  name: "Active Record"
  email: "active@example.com"
  status: 1
  organization: one

inactive:
  name: "Inactive Record"
  email: "inactive@example.com"
  status: 2
  organization: one
```

## Step 4: Run Test (Verify RED)

```bash
bin/rails test test/models/model_name_test.rb
```

Expected: Failure because model/table doesn't exist.

## Step 5: Generate Migration

```bash
bin/rails generate migration CreateModelNames \
  name:string \
  email:string:uniq \
  status:integer \
  organization:references
```

Review the generated migration and add:
- Null constraints: `null: false`
- Defaults: `default: 0`
- Indexes: `add_index :table, :column`

For tenant ownership columns, follow the multi-tenant convention: use an indexed UUID `account_id` without a database foreign key unless the project explicitly opts into hard tenant FKs.

```ruby
# db/migrate/YYYYMMDDHHMMSS_create_model_names.rb
class CreateModelNames < ActiveRecord::Migration[8.0]
  def change
    create_table :model_names do |t|
      t.string :name, null: false
      t.string :email, null: false
      t.integer :status, null: false, default: 0
      t.references :organization, null: false, foreign_key: true
      # Tenant ownership example:
      # t.references :account, null: false, type: :uuid, foreign_key: false, index: true

      t.timestamps
    end

    add_index :model_names, :email, unique: true
    add_index :model_names, :status
  end
end
```

## Step 6: Run Migration

```bash
bin/rails db:migrate
```

Verify with:
```bash
bin/rails db:migrate:status
```

## Step 7: Create Model File

Location: `app/models/[model_name].rb`

```ruby
# frozen_string_literal: true

class ModelName < ApplicationRecord
end
```

## Step 8: Run Test (Still RED)

```bash
bin/rails test test/models/model_name_test.rb
```

Expected: Failures for missing validations/associations.

## Step 9: Add Validations & Associations

```ruby
# frozen_string_literal: true

class ModelName < ApplicationRecord
  # === Associations ===
  belongs_to :organization
  has_many :posts, dependent: :destroy

  # === Enums ===
  enum :status, { pending: 0, active: 1, suspended: 2 }

  # === Validations ===
  validates :name, presence: true,
                   uniqueness: true,
                   length: { maximum: 100 }
  validates :email, presence: true,
                    uniqueness: { case_sensitive: false },
                    format: { with: URI::MailTo::EMAIL_REGEXP }

  # === Scopes ===
  scope :active, -> { where(status: :active) }
  scope :recent, -> { order(created_at: :desc) }

  # === Instance Methods ===
  def full_name
    "#{first_name} #{last_name}".strip
  end
end
```

## Step 10: Run Test (GREEN)

```bash
bin/rails test test/models/model_name_test.rb
```

All tests should pass.

## References

- See [templates/model_test.erb](templates/model_test.erb) for test template
- See [reference/validations.md](reference/validations.md) for validation patterns
- See [reference/domain-patterns.md](reference/domain-patterns.md) for rich model philosophy, pattern catalog, associations, scopes, callbacks, enums, delegation, business logic methods, `_later`/`_now` convention, and Current usage

## Common Patterns

### Enum with Validation

```ruby
enum :status, { draft: 0, published: 1, archived: 2 }
validates :status, inclusion: { in: statuses.keys }
```

### Polymorphic Association

```ruby
belongs_to :commentable, polymorphic: true
```

### Counter Cache

```ruby
belongs_to :organization, counter_cache: true
# Add: organization.posts_count column
```

### Soft Delete

```ruby
scope :active, -> { where(deleted_at: nil) }
scope :deleted, -> { where.not(deleted_at: nil) }

def soft_delete
  update(deleted_at: Time.current)
end
```
