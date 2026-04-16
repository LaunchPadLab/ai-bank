# Database Migration Domain Patterns

Recovered from migration-agent.md — comprehensive migration patterns for Rails 8 with UUIDs, multi-tenancy, and no foreign key constraints.

## Core Philosophy

**Simple schemas. UUIDs everywhere. No foreign key constraints.**

### Why UUIDs over integers:
- Non-sequential (security, no enumeration)
- Globally unique (easier data migrations)
- Can generate client-side
- No coordination needed across databases
- Safe for public URLs

### Why no foreign key constraints:
- Flexibility for data migrations
- Easier to delete records in development
- Simpler backup/restore
- No cascading delete surprises
- Application enforces referential integrity

### Why every table needs account_id:
- Multi-tenancy support
- Easy data scoping
- Query performance (indexed)
- Data isolation

---

## Migration Patterns

### Pattern 1: Creating a primary resource table

```ruby
class CreateCards < ActiveRecord::Migration[8.2]
  def change
    create_table :cards, id: :uuid do |t|
      t.references :account, null: false, type: :uuid, index: true

      t.references :board, null: false, type: :uuid, index: true
      t.references :column, null: false, type: :uuid, index: true

      t.references :creator, null: false, type: :uuid, index: true

      t.string :title, null: false
      t.text :body
      t.string :status, default: "draft", null: false
      t.string :color
      t.integer :position

      t.timestamps
    end

    add_index :cards, [:board_id, :position]
    add_index :cards, [:account_id, :status]
    add_index :cards, [:column_id, :position]
  end
end
```

### Pattern 2: Creating a state record table

```ruby
class CreateClosures < ActiveRecord::Migration[8.2]
  def change
    create_table :closures, id: :uuid do |t|
      t.references :account, null: false, type: :uuid, index: true
      t.references :card, null: false, type: :uuid, index: true
      t.references :user, null: true, type: :uuid, index: true
      t.text :reason
      t.timestamps
    end

    add_index :closures, :card_id, unique: true
  end
end
```

### Pattern 3: Creating a join table

```ruby
class CreateAssignments < ActiveRecord::Migration[8.2]
  def change
    create_table :assignments, id: :uuid do |t|
      t.references :account, null: false, type: :uuid, index: true
      t.references :card, null: false, type: :uuid, index: true
      t.references :user, null: false, type: :uuid, index: true
      t.timestamps
    end

    add_index :assignments, [:card_id, :user_id], unique: true
    add_index :assignments, [:user_id, :card_id]
  end
end
```

### Pattern 4: Creating a polymorphic table

```ruby
class CreateComments < ActiveRecord::Migration[8.2]
  def change
    create_table :comments, id: :uuid do |t|
      t.references :account, null: false, type: :uuid, index: true
      t.references :commentable, null: false, type: :uuid, polymorphic: true
      t.references :creator, null: false, type: :uuid, index: true

      t.text :body, null: false
      t.boolean :system, default: false

      t.timestamps
    end

    add_index :comments, [:commentable_type, :commentable_id]
    add_index :comments, [:account_id, :created_at]
  end
end
```

### Pattern 5: Creating a user/identity table

```ruby
class CreateIdentities < ActiveRecord::Migration[8.2]
  def change
    create_table :identities, id: :uuid do |t|
      t.string :email_address, null: false
      t.string :password_digest
      t.timestamps
    end

    add_index :identities, :email_address, unique: true
  end
end

class CreateUsers < ActiveRecord::Migration[8.2]
  def change
    create_table :users, id: :uuid do |t|
      t.references :identity, null: false, type: :uuid, index: true
      t.references :account, null: true, type: :uuid, index: true

      t.string :full_name, null: false
      t.string :timezone, default: "UTC"
      t.string :avatar_url

      t.timestamps
    end

    add_index :users, :identity_id, unique: true
  end
end
```

### Pattern 6: Creating a session/token table

```ruby
class CreateSessions < ActiveRecord::Migration[8.2]
  def change
    create_table :sessions, id: :uuid do |t|
      t.references :identity, null: false, type: :uuid, index: true
      t.string :token, null: false
      t.string :user_agent
      t.string :ip_address
      t.timestamps
    end

    add_index :sessions, :token, unique: true
    add_index :sessions, :created_at
  end
end
```

### Pattern 7: Adding columns to existing table

```ruby
class AddColorToCards < ActiveRecord::Migration[8.2]
  def change
    add_column :cards, :color, :string
    add_column :cards, :priority, :integer, default: 0
    add_index :cards, :color
  end
end
```

### Pattern 8: Adding references

```ruby
class AddParentToCards < ActiveRecord::Migration[8.2]
  def change
    add_reference :cards, :parent, type: :uuid, null: true, index: true
  end
end
```

### Pattern 9: Removing columns (safe)

```ruby
class RemoveClosedFromCards < ActiveRecord::Migration[8.2]
  def change
    safety_assured do
      remove_column :cards, :closed, :boolean
      remove_column :cards, :closed_at, :datetime
    end
  end
end
```

### Pattern 10: Renaming columns

```ruby
class RenameCardBodyToDescription < ActiveRecord::Migration[8.2]
  def change
    rename_column :cards, :body, :description
  end
end
```

---

## Index Strategies

### Single column indexes

```ruby
add_index :cards, :status
add_index :cards, :color
add_index :identities, :email_address, unique: true
add_index :cards, :board_id
add_index :cards, :account_id
```

### Composite indexes

```ruby
add_index :cards, [:board_id, :position]
add_index :cards, [:account_id, :status]
add_index :cards, [:column_id, :position]

# Order matters! Index [:a, :b] helps queries on:
# - WHERE a = ? AND b = ?
# - WHERE a = ?
# But NOT: WHERE b = ?
```

### Unique indexes

```ruby
add_index :closures, :card_id, unique: true
add_index :users, :identity_id, unique: true
add_index :assignments, [:card_id, :user_id], unique: true
```

### Partial indexes (PostgreSQL)

```ruby
add_index :cards, :board_id, where: "status = 'published'"
add_index :cards, :parent_id, where: "parent_id IS NOT NULL"
```

---

## Data Type Patterns

### String columns

```ruby
t.string :title           # VARCHAR(255)
t.string :status          # For enums
t.string :email_address   # For emails
t.string :color           # For hex colors
t.text :body              # For long content
t.text :description       # Unlimited length
```

### Numeric columns

```ruby
t.integer :position       # For ordering
t.integer :priority       # For rankings
t.decimal :price, precision: 10, scale: 2  # For money
t.float :rating           # For decimals
```

### Boolean columns

```ruby
# Avoid booleans for business state — use state records instead
# Only for true configuration flags:
t.boolean :admin, default: false, null: false
t.boolean :system, default: false
```

### Date/time columns

```ruby
t.datetime :published_at  # For state transitions
t.datetime :deleted_at    # For soft deletes
t.date :due_date          # For deadlines
t.timestamps              # created_at + updated_at
```

### JSON columns (PostgreSQL)

```ruby
t.jsonb :settings, default: {}
t.jsonb :metadata, default: {}
t.jsonb :particulars, default: {}
```

### Array columns (PostgreSQL)

```ruby
t.string :tags, array: true, default: []
add_index :cards, :tags, using: :gin
```

---

## Null Constraints

### When to use null: false

```ruby
# Always for multi-tenancy
t.references :account, null: false, type: :uuid

# Always for required associations
t.references :board, null: false, type: :uuid

# Always for required attributes
t.string :title, null: false
t.string :email_address, null: false

# Always for columns with defaults
t.string :status, default: "draft", null: false
t.boolean :admin, default: false, null: false
```

### When to use null: true (or omit)

```ruby
# Optional associations
t.references :parent, null: true, type: :uuid
t.references :user, null: true, type: :uuid

# Optional attributes
t.text :body
t.string :color
t.datetime :published_at
```

---

## Default Values

```ruby
t.string :status, default: "draft", null: false
t.string :timezone, default: "UTC"
t.boolean :admin, default: false, null: false
t.boolean :verified, default: false
t.integer :position, default: 0
t.integer :priority, default: 0
t.jsonb :settings, default: {}
t.timestamps  # Sets default: -> { CURRENT_TIMESTAMP }
```

---

## Special Column Patterns

### Timestamps (always include)

Use standard Rails timestamps on every table unless you have a rare, documented exception (e.g. a join with no audit need).

```ruby
t.timestamps
# Adds:
# - created_at (datetime, NOT NULL)
# - updated_at (datetime, NOT NULL)
```

For existing tables, use `add_timestamps :table_name` / `remove_timestamps :table_name` (see Common Migration Commands).

### Soft deletes

```ruby
t.datetime :deleted_at
add_index :cards, :deleted_at
```

### Token columns (for has_secure_token)

```ruby
t.string :token, null: false
add_index :sessions, :token, unique: true
```

### Counter caches

```ruby
t.integer :comments_count, default: 0, null: false
t.integer :cards_count, default: 0, null: false
```

---

## Migration Safety Patterns

### Safe operations (no downtime)

```ruby
add_column :cards, :color, :string
add_index :cards, :status, algorithm: :concurrently
create_table :new_table
add_reference :cards, :parent, type: :uuid
```

### Unsafe operations (require extra care)

```ruby
# Removing columns — deploy code removal first, then migrate
remove_column :cards, :old_field

# Changing column types
change_column :cards, :position, :bigint

# Renaming columns — use alias in model first
rename_column :cards, :body, :description

# Adding NOT NULL to existing column — backfill first
change_column_null :cards, :status, false
```

### Two-step migrations for safety

```ruby
# Step 1: Add column without default
class AddColorToCards < ActiveRecord::Migration[8.2]
  def change
    add_column :cards, :color, :string
  end
end

# Step 2: Backfill and add default
class BackfillColorOnCards < ActiveRecord::Migration[8.2]
  def up
    Card.in_batches.update_all(color: "blue")
    change_column_default :cards, :color, "blue"
  end

  def down
    change_column_default :cards, :color, nil
  end
end
```

---

## Reversible Migrations

### Automatically reversible

```ruby
def change
  create_table :cards
  add_column :cards, :color, :string
  add_index :cards, :status
  rename_column :cards, :body, :description
end
```

### Manually reversible

```ruby
def up
  Card.where(status: "active").update_all(status: "published")
end

def down
  Card.where(status: "published").update_all(status: "active")
end
```

### Irreversible migrations

```ruby
def up
  remove_column :cards, :old_field
end

def down
  raise ActiveRecord::IrreversibleMigration
end
```

---

## Data Migrations

### Backfilling data

```ruby
class BackfillAccountIdOnCards < ActiveRecord::Migration[8.2]
  def up
    Card.in_batches.each do |batch|
      batch.update_all("account_id = (SELECT account_id FROM boards WHERE boards.id = cards.board_id)")
    end
  end

  def down
    raise ActiveRecord::IrreversibleMigration
  end
end
```

### Migrating from boolean to state record

```ruby
class MigrateClosedToClosures < ActiveRecord::Migration[8.2]
  def up
    Card.where(closed: true).find_each do |card|
      Closure.create!(
        card: card,
        account: card.account,
        created_at: card.closed_at || card.updated_at
      )
    end
  end

  def down
    Closure.destroy_all
    Card.joins(:closure).update_all(closed: true)
  end
end
```

---

## Removing Foreign Key Constraints

```ruby
class RemoveAllForeignKeyConstraints < ActiveRecord::Migration[8.2]
  def up
    foreign_keys = ActiveRecord::Base.connection.tables.flat_map do |table|
      ActiveRecord::Base.connection.foreign_keys(table)
    end

    foreign_keys.each do |fk|
      remove_foreign_key fk.from_table, name: fk.name
    end
  end

  def down
    raise ActiveRecord::IrreversibleMigration
  end
end
```

---

## Testing Migrations

### Test in console

```ruby
# Rails console — fail fast if schema is behind
ActiveRecord::Migration.check_pending!

# Exercise a single migration class (same idea as migration tests)
CreateCards.new.migrate(:up)
CreateCards.new.migrate(:down)
```

Avoid calling `ActiveRecord::Migration.migrate(:up)` without arguments in console unless you intend to run the full pending migration set (same as `bin/rails db:migrate`).

```ruby
# test/db/migrate/create_cards_test.rb
require "test_helper"

class CreateCardsTest < ActiveSupport::TestCase
  def setup
    @migration = CreateCards.new
  end

  test "creates cards table" do
    @migration.migrate(:up)

    assert ActiveRecord::Base.connection.table_exists?(:cards)
    assert ActiveRecord::Base.connection.column_exists?(:cards, :title)
    assert ActiveRecord::Base.connection.column_exists?(:cards, :account_id)
  end

  test "migration is reversible" do
    @migration.migrate(:up)
    @migration.migrate(:down)

    assert_not ActiveRecord::Base.connection.table_exists?(:cards)
  end
end
```

---

## Schema.rb Patterns

```ruby
ActiveRecord::Schema[8.2].define(version: 2024_12_17_120000) do
  enable_extension "pgcrypto"

  create_table "cards", id: :uuid, default: -> { "gen_random_uuid()" }, force: :cascade do |t|
    t.uuid "account_id", null: false
    t.uuid "board_id", null: false
    t.uuid "column_id", null: false
    t.uuid "creator_id", null: false
    t.string "title", null: false
    t.text "body"
    t.string "status", default: "draft", null: false
    t.integer "position"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["account_id", "status"], name: "index_cards_on_account_id_and_status"
    t.index ["board_id", "position"], name: "index_cards_on_board_id_and_position"
    t.index ["column_id"], name: "index_cards_on_column_id"
  end
end
```

---

## Common Migration Commands

```ruby
# Tables
create_table :cards, id: :uuid
drop_table :cards
rename_table :old_name, :new_name

# Columns
add_column :cards, :color, :string
remove_column :cards, :color
rename_column :cards, :body, :description
change_column :cards, :position, :bigint
change_column_default :cards, :status, "draft"
change_column_null :cards, :title, false

# Indexes
add_index :cards, :status
add_index :cards, [:board_id, :position]
add_index :cards, :email, unique: true
remove_index :cards, :status
remove_index :cards, column: [:board_id, :position]

# References
add_reference :cards, :board, type: :uuid, null: false, index: true
remove_reference :cards, :board

# Timestamps
add_timestamps :cards
remove_timestamps :cards
```

---

## Migration Naming Conventions

```ruby
# Creating tables
CreateCards
CreateBoardPublications

# Adding columns
AddColorToCards
AddParentToCards
AddTimestampsToCards

# Removing columns
RemoveClosedFromCards
RemoveOldFieldsFromCards

# Changing columns
ChangeCardPositionToBigint
RenameCardBodyToDescription

# Data migrations
BackfillAccountIdOnCards
MigrateClosedToClosures

# Indexes
AddIndexOnCardsStatus
AddCompositeIndexOnCards
```

---

## Multi-database support

Migrations in `db/migrate` run against the **primary** database by default.

For [multiple databases](https://guides.rubyonrails.org/active_record_multiple_databases.html), configure each entry in `config/database.yml` and set `migrations_paths` for any non-primary database so its migrations live in a dedicated directory (for example `db/animals_migrate`).

```yaml
# Example shape — names and paths match your app
production:
  primary:
    database: app_primary
  animals:
    database: app_animals
    migrations_paths: db/animals_migrate
```

Run migrations per database with the generated tasks, for example:

```bash
bin/rails db:migrate                    # primary (default)
bin/rails db:migrate:animals          # matches the key under production:
```

Implement `connects_to` on models and use `ActiveRecord::Base.connected_to` in application code as needed; keep each migration class tied to one connection via its migration path and configuration rather than grabbing arbitrary connections from the pool.

---

## Boundaries

- **Always do:** Use UUIDs for primary keys (`id: :uuid`), add `account_id` to multi-tenant tables, add indexes on foreign keys, add timestamps, make migrations reversible, use `null: false` for required fields, use defaults for enums, index composite columns for common queries, test migrations up and down
- **Ask first:** Before adding foreign key constraints, before adding boolean columns for business state (use state records), before removing columns (two-step process), before changing column types (requires downtime), before adding NOT NULL to existing columns (backfill first)
- **Never do:** Add foreign key constraints, use integer primary keys, skip `account_id` on multi-tenant tables, skip timestamps, skip indexes on foreign keys, make irreversible migrations without good reason, use booleans for business state, forget to index common query patterns, deploy unsafe migrations without testing
