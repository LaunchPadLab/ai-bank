---
name: multi-tenant-patterns
description: URL-based multi-tenancy patterns, account scoping, Current attributes, membership management, data isolation, and migration strategies. Reference material for multi-tenant Rails applications.
user-invocable: false
---

# Multi-Tenant Patterns

## Philosophy: URL-Based Multi-Tenancy, Not Subdomain or Schema

**Approach:**
- URL-based: app.myapp.com/123/projects/456 (account_id in path)
- account_id on every table (no foreign key constraints)
- Current.account set from URL params for all requests
- All queries scoped through Current.account
- UUIDs everywhere (prevents enumeration attacks)
- Default scopes avoided (explicit scoping preferred)

**vs. Traditional Approaches:**
```ruby
# ❌ Subdomain-based: acme.myapp.com (DNS/SSL complexity)
# ❌ Schema-based: Apartment gem (migration nightmares)
# ❌ Default scopes: where(account_id: Current.account&.id) (implicit, hard to debug)
# ❌ User-derived: Current.account = current_user.account (no multi-account support)
# ❌ Missing account_id on tables (no data isolation)
```

**Good Way:**
```ruby
# ✅ URL-based routing
scope "/:account_id" do
  resources :boards do
    resources :cards
  end
end

# ✅ Current.account from URL
def set_current_account
  Current.account = current_user.accounts.find(params[:account_id])
end

# ✅ Explicit scoping
Current.account.boards.find(params[:id])

# ✅ account_id on every table with UUIDs
create_table :cards, id: :uuid do |t|
  t.references :board, null: false, type: :uuid
  t.references :account, null: false, type: :uuid
end
```

## Project Knowledge

**Rails Version:** 8.x
**Stack:**
- URL-based multi-tenancy: /accounts/:account_id/...
- Current attributes for account/user context
- UUIDs for all primary keys
- PostgreSQL (no schema separation)
- No Apartment gem, no subdomain routing

**Authentication:**
- Custom passwordless with Current.user
- Users can belong to multiple accounts
- Account membership controls access

**Database:**
- account_id on every table
- No foreign key constraints (for flexibility)
- UUIDs prevent enumeration
- Single database, single schema

## Commands

```bash
rails generate model Account name:string
rails generate model Membership user:references account:references role:integer
rails generate migration AddAccountToCards account:references
rails generate scaffold Board name:string account:references
```

## Pattern Index

### Pattern 1: Account Model and Memberships

Account has_many memberships has_many users. Membership model with enum roles (member/admin/owner). Account provides `member?`, `add_member`, `remove_member`, `owner` convenience methods. User provides `member_of?`, `role_in`, `admin_of?`, `owner_of?`. UUIDs on both tables with unique index on `[user_id, account_id]`.

### Pattern 2: Current Attributes for Request Context

Current stores user, account, and membership per-request. ApplicationController sets all three from session + URL params via before_actions. Includes `ensure_account_member`, `require_admin!`, `require_owner!` guards. Current provides `can_edit?` and `can_destroy?` convenience methods checking membership role.

### Pattern 3: URL-Based Routing

All resources nested under `scope "/:account_id"`. Authentication routes (sessions, magic links) live outside account scope. Account selection at root. Supports numeric IDs, `/a/:account_id` prefix, or slug-based (`/:account_slug`) routing variants. Path helpers always include Current.account.

### Pattern 4: Account-Scoped Models

Every model includes `belongs_to :account` with presence validation. `before_validation :set_account, on: :create` sets account from Current or parent association. Cross-association validation ensures `account_matches_board`. Extractable to an `AccountScoped` concern for DRY inclusion.

### Pattern 5: Account-Scoped Controllers

All queries go through `Current.account.boards.find(params[:id])`. Nested resources use double-scoping: `@board = Current.account.boards.find(params[:board_id])` then `@card = @board.cards.find(params[:id])`. Explicit account assignment on create. Extractable to `AccountScopedController` concern.

### Pattern 6: Account Switching and Selection

AccountsController outside account scope for index/new/create. Auto-redirect to last accessed account (stored in session) or single account. Session stores `last_account_id` via after_action callback. View includes dropdown account switcher in nav.

### Pattern 7: Membership Management

Admin-gated MembershipsController for inviting/removing members. Finds users by email, creates membership with role. Owner self-removal prevention. MembershipMailer sends invitation emails. Views show member table with role badges and remove buttons.

### Pattern 8: Data Isolation and Security

`AccountIsolation` concern validates all belongs_to associations share the same account_id on create. `AccountSecurity` concern rescues RecordNotFound without revealing cross-account existence. `ensure_same_account` method for paranoid double-checking in controllers.

### Pattern 9: Cross-Account References

For rare cross-account needs (integrations, webhooks): use join tables like IntegrationAccount. Integration model has_many accounts through join table. `authorized_for?` checks account access. Account-scoped webhook endpoints POST to external URLs.

### Pattern 10: Account Migrations

Safe migration pattern: add nullable account reference, backfill from parent associations via SQL UPDATE...FROM, then change to non-null. Batch migration helper for adding account_id to multiple tables at once with association-chain backfill.

## Common Patterns

### Account-Scoped Queries
```ruby
Current.account.boards.find(params[:id])
Current.account.cards.where(column: column)

# Double-scoping for nested resources
@board = Current.account.boards.find(params[:board_id])
@card = @board.cards.find(params[:id])
```

### Setting Account on Create
```ruby
before_validation :set_account, on: :create

def set_account
  self.account ||= Current.account
end
```

### URL Helpers
```ruby
account_boards_path(Current.account)
account_board_path(Current.account, @board)
account_board_card_path(Current.account, @board, @card)
```

### Permission Checks
```ruby
def require_admin!
  unless Current.membership_admin?
    redirect_to account_path(Current.account), alert: "Admin access required"
  end
end

def can_edit?(resource)
  Current.membership_admin? || resource.creator == Current.user
end
```

## Performance Tips

1. **Index account_id Queries:** `add_index :cards, [:account_id, :created_at]`
2. **Eager Load Memberships:** `current_user.accounts.includes(:memberships)`
3. **Cache Current.account Lookups:** rescue RecordNotFound and redirect
4. **Use Counter Caches:** `belongs_to :account, counter_cache: :members_count`

## Boundaries

### Always:
- Include account_id on every tenant-scoped table
- Use UUIDs for all IDs (prevents enumeration)
- Scope all queries through Current.account
- Set Current.account from URL params (not session or user)
- Use URL-based routing: /:account_id/boards
- Validate account consistency across associations
- Store last accessed account in session
- Use belongs_to :account (not default_scope)
- Test cross-account access is prevented
- Index on [account_id, created_at] and [account_id, foreign_key]

### Ask First:
- Whether to use slugs vs numeric IDs in URLs
- Whether users can belong to multiple accounts
- Role hierarchy (owner, admin, member, guest)
- Cross-account resource references
- Account deletion policies
- Transfer ownership workflows

### Never:
- Use subdomain-based multi-tenancy (acme.app.com)
- Use schema-based multi-tenancy (Apartment gem)
- Use default_scope for account filtering
- Add foreign key constraints on account_id
- Set Current.account from current_user.account (should be from URL)
- Allow access to resources without checking account
- Forget to scope queries through Current.account
- Trust params[:account_id] without verifying membership
- Store account_id in session (URL is source of truth)
- Allow cross-account queries without explicit authorization

## Additional Resources

- [Detailed Patterns & Code Examples](reference/patterns.md) — Full implementation code for all 10 patterns including models, migrations, controllers, views, concerns, and complete test suites
