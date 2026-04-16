# Rails Controller Domain Patterns

## Core Philosophy: Everything is CRUD

When something doesn't fit standard CRUD, create a new resource. Never add custom actions.

### Bad (custom actions):
```ruby
# ❌ DON'T DO THIS
resources :cards do
  post :close
  post :reopen
  post :gild
  post :ungild
  post :postpone
end
```

### Good (new resources):
```ruby
# ✅ DO THIS
resources :cards do
  resource :closure      # POST to close, DELETE to reopen
  resource :goldness     # POST to gild, DELETE to ungild
  resource :not_now      # POST to postpone, DELETE to resume
  resource :pin          # POST to pin, DELETE to unpin
  resource :watch        # POST to watch, DELETE to unwatch

  scope module: :cards do
    resources :assignments
    resources :comments
  end
end
```

## State Change Controllers (Singular Resources)

```ruby
# app/controllers/cards/closures_controller.rb
class Cards::ClosuresController < ApplicationController
  include CardScoped  # Provides @card, @board

  def create
    @card.close(user: Current.user)
    render_card_replacement
  end

  def destroy
    @card.reopen
    render_card_replacement
  end
end
```

## Standard CRUD Controllers (Plural Resources)

```ruby
# app/controllers/cards/comments_controller.rb
class Cards::CommentsController < ApplicationController
  include CardScoped

  def index
    @comments = @card.comments.recent
  end

  def create
    @comment = @card.comments.create!(comment_params)

    respond_to do |format|
      format.turbo_stream
      format.html { redirect_to @card }
    end
  end

  private

  def comment_params
    params.require(:comment).permit(:body)
  end
end
```

## Nested Resource Pattern

```ruby
# app/controllers/boards/columns_controller.rb
class Boards::ColumnsController < ApplicationController
  include BoardScoped  # Provides @board

  def show
    @column = @board.columns.find(params[:id])
    @cards = @column.cards.positioned
  end

  def create
    @column = @board.columns.create!(column_params)

    respond_to do |format|
      format.turbo_stream
      format.html { redirect_to @board }
    end
  end

  def update
    @column = @board.columns.find(params[:id])
    @column.update!(column_params)

    head :no_content
  end

  def destroy
    @column = @board.columns.find(params[:id])
    @column.destroy!

    respond_to do |format|
      format.turbo_stream
      format.html { redirect_to @board }
    end
  end

  private

  def column_params
    params.require(:column).permit(:name, :position)
  end
end
```

## Resource Thinking

When a user asks to add functionality, ask: "What resource does this represent?"

| User request | Resource to create |
|---|---|
| "Let users close cards" | `Cards::ClosuresController` with create/destroy |
| "Let users mark important cards" | `Cards::GoldnessesController` |
| "Let users follow a card" | `Cards::WatchesController` |
| "Let users assign cards" | `Cards::AssignmentsController` with create/destroy |
| "Let users publish boards" | `Boards::PublicationsController` |
| "Let users position cards" | `Cards::PositionsController` with update |
| "Let users archive projects" | `Projects::ArchivalsController` |

## Routing Patterns

### Pattern 1: Singular resource for toggles

```ruby
resource :closure, only: [:create, :destroy]  # No :show, :edit, :new needed
```

### Pattern 2: Module scoping for organization

```ruby
resources :cards do
  scope module: :cards do
    resources :comments
    resources :attachments
    resource :closure
    resource :goldness
  end
end
```

### Pattern 3: Polymorphic routes with resolve

```ruby
resolve "Comment" do |comment, options|
  options[:anchor] = ActionView::RecordIdentifier.dom_id(comment)
  route_for :card, comment.card, options
end
```

### Pattern 4: Constraints for multi-tenancy

```ruby
scope "/:account_id", constraints: AccountSlug do
  resources :boards do
    # nested resources here
  end
end
```

## Controller Concerns

### CardScoped
Provides `@card` and `@board`. Use for any controller under `cards/`.

```ruby
include CardScoped
```

### BoardScoped
Provides `@board`. Use for any controller under `boards/`.

```ruby
include BoardScoped
```

### Creating new scoping concerns:
```ruby
# app/controllers/concerns/project_scoped.rb
module ProjectScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_project
  end

  private

  def set_project
    @project = Current.account.projects.find(params[:project_id])
  end
end
```

## Response Patterns

### Turbo Stream responses (preferred)

```ruby
respond_to do |format|
  format.turbo_stream
  format.html { redirect_to @resource }
end
```

### Multi-format responses

```ruby
def create
  @resource = Model.create!(resource_params)

  respond_to do |format|
    format.turbo_stream
    format.html { redirect_to @resource }
    format.json { render json: @resource, status: :created, location: @resource }
  end
end

def update
  @resource.update!(resource_params)

  respond_to do |format|
    format.turbo_stream
    format.html { redirect_to @resource }
    format.json { head :no_content }
  end
end

def destroy
  @resource.destroy!

  respond_to do |format|
    format.turbo_stream
    format.html { redirect_to @resources_path }
    format.json { head :no_content }
  end
end
```

## Standards

### Naming conventions
- **Controllers:** Plural for collections (`CommentsController`), singular for toggles (`ClosureController`)
- **Actions:** Only the 7 REST actions: `index`, `show`, `new`, `create`, `edit`, `update`, `destroy`
- **Routes:** Match controller name exactly

### Strong parameters

```ruby
private

def card_params
  params.require(:card).permit(:title, :body, :column_id, :color)
end
```

### Authorization

```ruby
before_action :ensure_can_administer_card, only: [:destroy]

private

def ensure_can_administer_card
  head :forbidden unless Current.user.can_administer_card?(@card)
end
```

## Files to Create

When generating a new resource controller, create:

1. **Controller file:** `app/controllers/[namespace]/[resource]_controller.rb`
2. **Route entry:** Add to `config/routes.rb`
3. **Test file:** `test/controllers/[namespace]/[resource]_controller_test.rb`
4. **Concern (if needed):** `app/controllers/concerns/[resource]_scoped.rb`
