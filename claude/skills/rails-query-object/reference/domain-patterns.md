# Query Object Domain Patterns

## Query Object Design Principles

### What is a Query Object?

A Query Object encapsulates complex database queries in a reusable, testable class. It keeps your models, controllers, and views free from complex ActiveRecord chains.

**Use Query Objects For:**
- Complex queries with multiple conditions
- Queries used in multiple places
- Queries with business logic
- Search and filtering logic
- Reporting queries
- Queries that need to be tested independently

**Don't Use Query Objects For:**
- Simple one-liner queries (use scopes)
- Queries used only once
- Basic associations

### N+1 Prevention

Always use `includes`, `preload`, or `eager_load`. Consider `strict_loading` in Rails 8+:
```ruby
class Entity < ApplicationRecord
  self.strict_loading_by_default = true
end
```

### Query Object vs Scope

```ruby
# BAD - Complex query in controller
class EntitiesController < ApplicationController
  def index
    @entities = Entity
      .joins(:user)
      .where(status: params[:status]) if params[:status].present?
      .where('created_at >= ?', params[:from_date]) if params[:from_date].present?
      .where('name ILIKE ?', "%#{params[:q]}%") if params[:q].present?
      .order(created_at: :desc)
      .page(params[:page])
  end
end

# GOOD - Simple scope in model
class Entity < ApplicationRecord
  scope :published, -> { where(status: 'published') }
  scope :recent, -> { order(created_at: :desc) }
end

# GOOD - Complex query in Query Object
class Entities::SearchQuery
  def initialize(relation = Entity.all)
    @relation = relation
  end

  def call(params = {})
    @relation
      .then { |rel| filter_by_status(rel, params[:status]) }
      .then { |rel| filter_by_date(rel, params[:from_date]) }
      .then { |rel| search_by_name(rel, params[:q]) }
      .order(created_at: :desc)
  end

  private

  def filter_by_status(relation, status)
    return relation if status.blank?
    relation.where(status: status)
  end

  def filter_by_date(relation, from_date)
    return relation if from_date.blank?
    relation.where('created_at >= ?', from_date)
  end

  def search_by_name(relation, query)
    return relation if query.blank?
    relation.where('name ILIKE ?', "%#{sanitize_sql_like(query)}%")
  end
end
```

## ApplicationQuery Base Class

```ruby
# app/queries/application_query.rb
class ApplicationQuery
  attr_reader :relation

  def initialize(relation = default_relation)
    @relation = relation
  end

  def call(params = {})
    raise NotImplementedError, "#{self.class} must implement #call"
  end

  def self.call(*args)
    new.call(*args)
  end

  private

  def default_relation
    raise NotImplementedError, "#{self.class} must implement #default_relation"
  end

  def sanitize_sql_like(string)
    ActiveRecord::Base.sanitize_sql_like(string)
  end
end
```

### Basic Query Object Structure

```ruby
# app/queries/entities/search_query.rb
module Entities
  class SearchQuery < ApplicationQuery
    def call(filters = {})
      relation
        .then { |rel| filter_by_status(rel, filters[:status]) }
        .then { |rel| filter_by_user(rel, filters[:user_id]) }
        .then { |rel| search(rel, filters[:q]) }
        .then { |rel| sort(rel, filters[:sort]) }
    end

    private

    def default_relation
      Entity.includes(:user)
    end

    def filter_by_status(relation, status)
      return relation if status.blank?
      relation.where(status: status)
    end

    def filter_by_user(relation, user_id)
      return relation if user_id.blank?
      relation.where(user_id: user_id)
    end

    def search(relation, query)
      return relation if query.blank?

      relation.where(
        'name ILIKE :q OR description ILIKE :q',
        q: "%#{sanitize_sql_like(query)}%"
      )
    end

    def sort(relation, sort_param)
      case sort_param
      when 'name' then relation.order(name: :asc)
      when 'oldest' then relation.order(created_at: :asc)
      else relation.order(created_at: :desc)
      end
    end
  end
end
```

## Common Query Object Patterns

### 1. Search Query with Multiple Filters

```ruby
# app/queries/posts/search_query.rb
module Posts
  class SearchQuery < ApplicationQuery
    ALLOWED_STATUSES = %w[draft published archived].freeze
    ALLOWED_SORT_FIELDS = %w[title created_at updated_at].freeze

    def call(filters = {})
      relation
        .then { |rel| filter_by_status(rel, filters[:status]) }
        .then { |rel| filter_by_author(rel, filters[:author_id]) }
        .then { |rel| filter_by_category(rel, filters[:category_id]) }
        .then { |rel| filter_by_date_range(rel, filters[:from_date], filters[:to_date]) }
        .then { |rel| search_text(rel, filters[:q]) }
        .then { |rel| sort(rel, filters[:sort_by], filters[:sort_dir]) }
    end

    private

    def default_relation
      Post.includes(:author, :category)
    end

    def filter_by_status(relation, status)
      return relation if status.blank?
      return relation unless ALLOWED_STATUSES.include?(status)

      relation.where(status: status)
    end

    def filter_by_author(relation, author_id)
      return relation if author_id.blank?
      relation.where(author_id: author_id)
    end

    def filter_by_category(relation, category_id)
      return relation if category_id.blank?
      relation.where(category_id: category_id)
    end

    def filter_by_date_range(relation, from_date, to_date)
      relation = relation.where('created_at >= ?', from_date) if from_date.present?
      relation = relation.where('created_at <= ?', to_date) if to_date.present?
      relation
    end

    def search_text(relation, query)
      return relation if query.blank?

      sanitized = sanitize_sql_like(query)
      relation.where(
        'title ILIKE :q OR body ILIKE :q',
        q: "%#{sanitized}%"
      )
    end

    def sort(relation, field, direction)
      field = 'created_at' unless ALLOWED_SORT_FIELDS.include?(field)
      direction = direction == 'asc' ? :asc : :desc

      relation.order(field => direction)
    end
  end
end
```

### 2. Reporting Query with Aggregations

```ruby
# app/queries/orders/revenue_report_query.rb
module Orders
  class RevenueReportQuery < ApplicationQuery
    def call(start_date:, end_date:, group_by: :day)
      relation
        .where(created_at: start_date..end_date)
        .where(status: %w[paid delivered])
        .group_by_period(group_by, :created_at)
        .select(
          date_trunc_sql(group_by),
          'COUNT(*) as orders_count',
          'SUM(total) as total_revenue',
          'AVG(total) as average_order_value'
        )
    end

    private

    def default_relation
      Order.all
    end

    def date_trunc_sql(period)
      case period
      when :hour then "DATE_TRUNC('hour', created_at) as period"
      when :day then "DATE_TRUNC('day', created_at) as period"
      when :week then "DATE_TRUNC('week', created_at) as period"
      when :month then "DATE_TRUNC('month', created_at) as period"
      else "DATE_TRUNC('day', created_at) as period"
      end
    end
  end
end
```

### 3. Complex Join Query

```ruby
# app/queries/users/active_users_query.rb
module Users
  class ActiveUsersQuery < ApplicationQuery
    def call(days: 30)
      relation
        .joins(:posts, :comments)
        .where('posts.created_at >= ? OR comments.created_at >= ?', days.days.ago, days.days.ago)
        .distinct
        .select(
          'users.*',
          'COUNT(DISTINCT posts.id) as posts_count',
          'COUNT(DISTINCT comments.id) as comments_count'
        )
        .group('users.id')
        .having('COUNT(DISTINCT posts.id) > 0 OR COUNT(DISTINCT comments.id) > 0')
        .order('posts_count + comments_count DESC')
    end

    private

    def default_relation
      User.all
    end
  end
end
```

### 4. Scope-Based Dashboard Query

```ruby
# app/queries/entities/dashboard_query.rb
module Entities
  class DashboardQuery < ApplicationQuery
    def call(filters = {})
      relation
        .then { |rel| filter_by_status(rel, filters[:status]) }
        .then { |rel| filter_by_priority(rel, filters[:priority]) }
        .then { |rel| filter_by_period(rel, filters[:period]) }
    end

    private

    def default_relation
      Entity.includes(:user, :category)
    end

    def filter_by_status(relation, status)
      return relation if status.blank?
      relation.where(status: status)
    end

    def filter_by_priority(relation, priority)
      return relation if priority.blank?
      relation.where(priority: priority)
    end

    def filter_by_period(relation, period)
      case period
      when 'today'
        relation.where('created_at >= ?', Time.current.beginning_of_day)
      when 'week'
        relation.where('created_at >= ?', 1.week.ago)
      when 'month'
        relation.where('created_at >= ?', 1.month.ago)
      else
        relation
      end
    end
  end
end
```

### 5. Full-Text Search Query

```ruby
# app/queries/articles/full_text_search_query.rb
module Articles
  class FullTextSearchQuery < ApplicationQuery
    def call(query)
      return relation.none if query.blank?

      sanitized_query = sanitize_sql_like(query)
      search_terms = sanitized_query.split.map { |term| "%#{term}%" }

      relation
        .where(build_search_condition(search_terms))
        .order(Arel.sql(
          "ts_rank(to_tsvector('english', title || ' ' || body), plainto_tsquery('english', ?)) DESC"
        ), query)
    end

    private

    def default_relation
      Article.published.includes(:author)
    end

    def build_search_condition(terms)
      conditions = terms.map do |term|
        "title ILIKE :term OR body ILIKE :term OR author.name ILIKE :term"
      end

      [conditions.join(' OR '), { term: terms }]
    end
  end
end
```

### 6. Geolocation Query

```ruby
# app/queries/locations/nearby_query.rb
module Locations
  class NearbyQuery < ApplicationQuery
    EARTH_RADIUS_KM = 6371.0

    def call(latitude:, longitude:, radius_km: 10)
      relation
        .select(
          'locations.*',
          distance_sql(latitude, longitude)
        )
        .having("distance <= ?", radius_km)
        .order('distance ASC')
    end

    private

    def default_relation
      Location.all
    end

    def distance_sql(lat, lng)
      <<~SQL
        (
          #{EARTH_RADIUS_KM} * acos(
            cos(radians(#{lat})) *
            cos(radians(latitude)) *
            cos(radians(longitude) - radians(#{lng})) +
            sin(radians(#{lat})) *
            sin(radians(latitude))
          )
        ) as distance
      SQL
    end
  end
end
```

### 7. Pagination-Aware Query

```ruby
# app/queries/products/catalog_query.rb
module Products
  class CatalogQuery < ApplicationQuery
    def call(filters = {}, page: 1, per_page: 20)
      relation
        .then { |rel| filter_by_category(rel, filters[:category]) }
        .then { |rel| filter_by_price_range(rel, filters[:min_price], filters[:max_price]) }
        .then { |rel| filter_by_availability(rel, filters[:in_stock]) }
        .then { |rel| sort(rel, filters[:sort]) }
        .page(page)
        .per(per_page)
    end

    private

    def default_relation
      Product.includes(:category, :reviews)
    end

    def filter_by_category(relation, category_id)
      return relation if category_id.blank?
      relation.where(category_id: category_id)
    end

    def filter_by_price_range(relation, min_price, max_price)
      relation = relation.where('price >= ?', min_price) if min_price.present?
      relation = relation.where('price <= ?', max_price) if max_price.present?
      relation
    end

    def filter_by_availability(relation, in_stock)
      return relation if in_stock.blank?

      case in_stock
      when 'true', true
        relation.where('stock > 0')
      when 'false', false
        relation.where(stock: 0)
      else
        relation
      end
    end

    def sort(relation, sort_param)
      case sort_param
      when 'price_asc' then relation.order(price: :asc)
      when 'price_desc' then relation.order(price: :desc)
      when 'name' then relation.order(name: :asc)
      when 'popular' then relation.order(views_count: :desc)
      else relation.order(created_at: :desc)
      end
    end
  end
end
```

## Usage in Controllers

```ruby
class EntitiesController < ApplicationController
  def index
    @entities = Entities::SearchQuery
      .new
      .call(search_params)
      .page(params[:page])
  end

  private

  def search_params
    params.permit(:status, :user_id, :q, :sort)
  end
end
```

## Minitest Query Tests

### Basic Query Tests

```ruby
# test/queries/entities/search_query_test.rb
require "test_helper"

class Entities::SearchQueryTest < ActiveSupport::TestCase
  setup do
    @published_entity = Entity.create!(status: "published", name: "Alpha")
    @draft_entity = Entity.create!(status: "draft", name: "Beta")
    @archived_entity = Entity.create!(status: "archived", name: "Gamma")
  end

  test "returns all entities without filters" do
    results = Entities::SearchQuery.new.call({})
    assert_equal 3, results.size
  end

  test "orders by created_at desc by default" do
    results = Entities::SearchQuery.new.call({})
    assert_equal @archived_entity, results.first
  end

  test "filters by status" do
    results = Entities::SearchQuery.new.call(status: "published")
    assert_equal [@published_entity], results.to_a
  end

  test "searches by name" do
    results = Entities::SearchQuery.new.call(q: "alpha")
    assert_equal [@published_entity], results.to_a
  end

  test "search is case insensitive" do
    results = Entities::SearchQuery.new.call(q: "ALPHA")
    assert_equal [@published_entity], results.to_a
  end

  test "sorts by name ascending" do
    results = Entities::SearchQuery.new.call(sort: "name")
    assert_equal %w[Alpha Beta Gamma], results.pluck(:name)
  end

  test "applies multiple filters" do
    results = Entities::SearchQuery.new.call(status: "published", q: "alpha")
    assert_equal [@published_entity], results.to_a
  end
end
```

### Testing Complex Queries

```ruby
# test/queries/users/active_users_query_test.rb
require "test_helper"

class Users::ActiveUsersQueryTest < ActiveSupport::TestCase
  setup do
    @active_user = users(:one)
    @inactive_user = users(:two)
    @recently_active_user = users(:three)

    Post.create!(user: @active_user, created_at: 10.days.ago)
    Comment.create!(user: @active_user, created_at: 5.days.ago)
    Post.create!(user: @inactive_user, created_at: 60.days.ago)
    Comment.create!(user: @recently_active_user, created_at: 2.days.ago)
  end

  test "returns users active in the last 30 days" do
    results = Users::ActiveUsersQuery.new.call(days: 30)
    assert_includes results, @active_user
    assert_includes results, @recently_active_user
  end

  test "excludes inactive users" do
    results = Users::ActiveUsersQuery.new.call(days: 30)
    assert_not_includes results, @inactive_user
  end

  test "orders by activity count" do
    results = Users::ActiveUsersQuery.new.call(days: 30)
    assert_equal @active_user, results.first
  end

  test "includes activity counts" do
    results = Users::ActiveUsersQuery.new.call(days: 30)
    user = results.find { |u| u.id == @active_user.id }
    assert_equal 1, user.posts_count
    assert_equal 1, user.comments_count
  end
end
```

### Testing Query Performance

```ruby
# test/queries/posts/search_query_test.rb
require "test_helper"

class Posts::SearchQueryTest < ActiveSupport::TestCase
  test "avoids N+1 queries" do
    3.times { Post.create!(author: users(:one), category: categories(:one)) }

    query = Posts::SearchQuery.new
    query.call({})

    query_count = count_queries do
      results = query.call({})
      results.each do |post|
        post.author.name
        post.category.name
      end
    end

    assert query_count <= 3, "Expected at most 3 queries, got #{query_count}"
  end

  private

  def count_queries(&block)
    count = 0
    counter = ->(*) { count += 1 }
    ActiveSupport::Notifications.subscribed(counter, "sql.active_record", &block)
    count
  end
end
```

## Query Optimization Tips

### 1. Always Include Necessary Associations

```ruby
# BAD - N+1 queries
def default_relation
  Entity.all
end

# GOOD - Preload associations
def default_relation
  Entity.includes(:user, :submissions)
end
```

### 2. Use `then` for Chainable Filters

```ruby
relation
  .then { |rel| filter_by_status(rel, status) }
  .then { |rel| filter_by_user(rel, user_id) }
  .then { |rel| search(rel, query) }
```

### 3. Sanitize User Input

```ruby
def search(relation, query)
  return relation if query.blank?

  relation.where(
    'name ILIKE ?',
    "%#{sanitize_sql_like(query)}%"
  )
end
```

### 4. Use Parameterized Queries

```ruby
# BAD - SQL injection risk
relation.where("name = '#{query}'")

# GOOD - Parameterized
relation.where('name = ?', query)
relation.where(name: query)
```
