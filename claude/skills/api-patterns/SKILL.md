---
name: api-patterns
description: REST API patterns with respond_to blocks, Jbuilder templates, token auth, error handling, and pagination for Rails. Reference material for API development.
user-invocable: false
---

# API Patterns

## Philosophy: Same Controllers, Different Formats

- One controller serves both HTML (web) and JSON (API)
- Use `respond_to` blocks for format-specific responses
- RESTful routes only (no GraphQL, no custom endpoints unless absolutely necessary)
- Jbuilder for JSON templates (like ERB for HTML)
- HTTP status codes for success/errors
- Token-based authentication for API (not OAuth unless required)
- Versioning through Accept headers or URL prefixes when needed

**vs. Traditional Approaches:**
```ruby
# ❌ BAD: Separate API controllers
class Api::V1::BoardsController < Api::BaseController
  def index
    render json: Board.all
  end
end

class BoardsController < ApplicationController
  def index
    @boards = Board.all
  end
end

# ❌ BAD: GraphQL (too complex for most needs)
field :boards, [BoardType], null: false

# ❌ BAD: Active Model Serializers (extra dependency)
class BoardSerializer < ActiveModel::Serializer
  attributes :id, :name
end

# ❌ BAD: Inline JSON in controller
def show
  render json: {
    id: @board.id,
    name: @board.name,
    cards: @board.cards.map { |c| { id: c.id, title: c.title } }
  }
end
```

**Good Way:**
```ruby
# ✅ GOOD: One controller, multiple formats
class BoardsController < ApplicationController
  def index
    @boards = Current.account.boards.includes(:creator)

    respond_to do |format|
      format.html # renders index.html.erb
      format.json # renders index.json.jbuilder
    end
  end

  def show
    @board = Current.account.boards.find(params[:id])

    respond_to do |format|
      format.html
      format.json
    end
  end
end

# ✅ GOOD: Jbuilder templates for JSON
# app/views/boards/index.json.jbuilder
json.array! @boards do |board|
  json.id board.id
  json.name board.name
  json.created_at board.created_at
  json.url board_url(board)
end

# ✅ GOOD: RESTful API design
GET    /boards          - List boards
GET    /boards/:id      - Show board
POST   /boards          - Create board
PATCH  /boards/:id      - Update board
DELETE /boards/:id      - Delete board
```

## Pattern Index

1. **Respond To Blocks** — One controller for HTML + JSON with `respond_to` format switching
2. **Jbuilder Templates** — JSON view templates with partials, `extract!`, caching, and conditional attributes
3. **API Token Authentication** — Bearer token auth with `ApiToken` model and `ApiAuthenticatable` concern
4. **Error Handling** — `rescue_from` concern returning proper HTTP status codes and JSON error bodies
5. **HTTP Caching** — ETags and `stale?` for conditional GET responses
6. **Pagination** — Page-based (with headers) and cursor-based pagination strategies
7. **Nested Resources** — Parent/child relationships in JSON with embedded associations
8. **API Versioning** — URL namespacing (`/api/v1/`) or Accept header version negotiation
9. **Batch Operations** — Multi-record update/destroy in a single request
10. **Webhooks** — Event notification endpoints for API consumers

## Common Patterns

### Respond To Blocks
```ruby
respond_to do |format|
  format.html # renders view
  format.json # renders jbuilder
end
```

### Error Responses
```ruby
render json: { error: "Not found" }, status: :not_found
render json: @board.errors, status: :unprocessable_entity
```

### Token Authentication
```ruby
header = request.headers["Authorization"]
token = header&.match(/Bearer (.+)/)&.captures&.first
@api_token = ApiToken.find_by(token: token)
```

### Jbuilder Partials
```ruby
json.partial! "boards/board", board: @board
json.array! @boards, partial: "boards/board", as: :board
```

### HTTP Caching
```ruby
if stale?(@board)
  render :show
end
```

## Performance Tips

1. **Eager Load Associations:**
```ruby
@boards = Current.account.boards.includes(:creator, :cards)
```

2. **Cache Jbuilder Fragments:**
```ruby
json.cache! @board do
  json.extract! @board, :id, :name
end
```

3. **Use ETags:**
```ruby
if stale?(@boards)
  render :index
end
```

4. **Paginate Collections:**
```ruby
@boards = Current.account.boards.page(params[:page]).per(25)
```

5. **Select Only Needed Columns:**
```ruby
@boards = Current.account.boards.select(:id, :name, :created_at)
```

## Additional Resources

- [Detailed pattern code examples](reference/patterns.md) — Full implementations for all 10 patterns plus testing examples
- For API versioning patterns, see [reference/versioning.md](reference/versioning.md)
