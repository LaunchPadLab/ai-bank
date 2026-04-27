---
name: "rails-query-object"
description: "Creates query objects for complex database queries following TDD. Use when encapsulating complex queries, aggregating statistics, building reports, or when user mentions queries, stats, dashboards, or data aggregation."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools. -->

# Rails Query Object Generator (TDD)

Creates query objects that encapsulate complex database queries with specs first.

## Quick Start

1. Write failing test in `test/queries/`
2. Run test to confirm RED
3. Implement query object in `app/queries/`
4. Run test to confirm GREEN

## Project Conventions

Query objects in this project:
- Accept context via constructor (`user:` or `account:`)
- Return `ActiveRecord::Relation` for chainability OR `Hash` for aggregations
- Have a `call` method for primary operation
- Support multi-tenancy (scoped to account)

## TDD Workflow

### Step 1: Create Query Test (RED)

```ruby
# test/queries/[name]_query_test.rb
require "test_helper"

class [Name]QueryTest < ActiveSupport::TestCase
  setup do
    @user = users(:one)
    @account = @user.account
    @other_account = users(:two).account

    # Fixtures scoped to current account
    @resource1 = resources(:one)       # account: @account
    @resource2 = resources(:two)       # account: @account

    # Fixture for other account (should not appear)
    @other_resource = resources(:other_account)

    @query = [Name]Query.new(account: @account)
  end

  test "requires an account parameter" do
    assert_raises(ArgumentError) { [Name]Query.new }
  end

  test "stores the account" do
    assert_equal @account, @query.account
  end

  test "returns expected result type" do
    assert_kind_of ActiveRecord::Relation, @query.call
    # OR for hash results:
    # assert_kind_of Hash, @query.call
  end

  test "only returns resources for the account (multi-tenant)" do
    result = @query.call
    assert_includes result, @resource1
    assert_includes result, @resource2
    refute_includes result, @other_resource
  end

  test "ensures account A cannot see account B data" do
    other_query = [Name]Query.new(account: @other_account)

    refute_includes @query.call, @other_resource
    refute_includes other_query.call, @resource1
  end
end
```

### Step 2: Run Test (Confirm RED)

```bash
bin/rails test test/queries/[name]_query_test.rb
```

### Step 3: Implement Query Object (GREEN)

```ruby
# app/queries/[name]_query.rb
class [Name]Query
  attr_reader :account

  def initialize(account:)
    @account = account
  end

  # Returns [description of result]
  # @return [ActiveRecord::Relation<Resource>] OR [Hash]
  def call
    account.resources
      .where(condition: value)
      .order(created_at: :desc)
  end
end
```

### Step 4: Run Test (Confirm GREEN)

```bash
bin/rails test test/queries/[name]_query_test.rb
```

## Query Object Patterns

### Pattern 1: Simple Filtered Query

```ruby
# app/queries/stale_leads_query.rb
class StaleLeadsQuery
  attr_reader :account

  def initialize(account:)
    @account = account
  end

  def call
    account.leads.stale
  end
end
```

### Pattern 2: Aggregation Query (Multiple Methods)

```ruby
# app/queries/dashboard_stats_query.rb
class DashboardStatsQuery
  attr_reader :user, :account

  def initialize(user:)
    @user = user
    @account = user.account
  end

  def upcoming_events(limit: 3)
    account.events
      .where("event_date >= ?", Date.today)
      .order(event_date: :asc)
      .limit(limit)
  end

  def pending_commissions_total
    EventVendor
      .joins(:event)
      .where(events: { account_id: account.id })
      .where(commission_status: :to_invoice)
      .sum(:commission_value)
  end

  def top_vendors(limit: 5)
    account.vendors
      .left_joins(:event_vendors)
      .select("vendors.*, COUNT(event_vendors.id) as events_count")
      .group("vendors.id")
      .order("events_count DESC")
      .limit(limit)
  end

  def leads_by_status
    account.leads.group(:status).count
  end
end
```

### Pattern 3: Grouping Query

```ruby
# app/queries/leads_by_status_query.rb
class LeadsByStatusQuery
  attr_reader :account

  def initialize(account:)
    @account = account
  end

  def call
    leads = account.leads.order(created_at: :desc)
    result = Lead.statuses.keys.map(&:to_sym).index_with { [] }

    leads.group_by(&:status).each do |status, status_leads|
      result[status.to_sym] = status_leads
    end

    result
  end
end
```

## Usage in Controllers

```ruby
# Simple query
def index
  @leads_by_status = LeadsByStatusQuery.new(account: current_account).call
end

# Aggregation query with presenter
def index
  stats_query = DashboardStatsQuery.new(user: current_user)
  @stats = DashboardStatsPresenter.new(stats_query)
end
```

## Checklist

- [ ] Test written first (RED)
- [ ] Constructor accepts context (`user:` or `account:`)
- [ ] Multi-tenant isolation tested
- [ ] Return type documented (`@return`)
- [ ] Methods have clear, descriptive names
- [ ] Complex queries use `.includes()` to prevent N+1
- [ ] All tests GREEN

## Reference

- [Domain Patterns](reference/domain-patterns.md) — ApplicationQuery base class, search/reporting/join/dashboard/geolocation/pagination query patterns, Minitest query tests, performance testing, query optimization tips
