---
name: "rails-architecture"
description: "Guides modern Rails 8 code architecture decisions and patterns. Use when deciding where to put code, choosing between patterns (service objects vs concerns vs query objects), designing feature architecture, refactoring for better organization, or when user mentions architecture, code organization, design patterns, or layered design."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools. -->

# Rails 8 Architecture: Convention First

## Overview

Rails 8 works best when the application uses the framework's conventions before inventing new layers. Favor RESTful controllers, rich Active Record models, Hotwire, Minitest, fixtures, and the app's configured Rails defaults.

The architecture goal is conceptual compression: fewer custom patterns, fewer translation layers, and code that another Rails developer can read without learning a private framework.

## Architecture Decision Tree

```
Where should this code go?
│
├─ Is it HTTP request/response handling?
│   └─ → Controller (standard REST action when possible)
│
├─ Is it cohesive behavior for one aggregate?
│   └─ → Model method, association, validation, scope, or state transition
│
├─ Is it shared horizontal behavior across models/controllers?
│   └─ → Concern (see: rails-concern skill)
│
├─ Is it read/query complexity?
│   ├─ Simple/reusable condition → Model scope
│   └─ Multi-join/reporting query → Query Object (see: rails-query-object skill)
│
├─ Is it input complexity across models or wizard steps?
│   └─ → Form Object (see: form-object-patterns skill)
│
├─ Is it authorization logic?
│   └─ → Policy (see: policy-patterns skill)
│
├─ Is it view/display formatting?
│   └─ → Presenter, helper, or ViewComponent depending on reuse and logic
│
├─ Is it reusable UI with logic?
│   └─ → ViewComponent (see: viewcomponent-patterns skill)
│
├─ Is it async/background work?
│   └─ → Job using the repo's configured queue backend
│
├─ Is it a transactional email?
│   └─ → Mailer (see: action-mailer-patterns skill)
│
├─ Is it real-time/WebSocket communication?
│   └─ → Channel (see: action-cable-patterns skill)
│
└─ Does it orchestrate multiple models, transactions, side effects, or external systems?
    └─ → Service Object (see: rails-service-object skill)
```

## Layer Interaction Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        REQUEST                               │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     CONTROLLER                               │
│  • Authenticate (Authentication concern)                     │
│  • Authorize (Policy)                                        │
│  • Parse params                                              │
│  • Load records, call model behavior, render/redirect         │
└──────────┬─────────────────────────────────┬────────────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────┐           ┌─────────────────────┐
│      SERVICE        │           │       QUERY         │
│  • Orchestration    │           │  • Complex queries  │
│  • Side effects     │           │  • Aggregations     │
│  • Transactions     │           │  • Reports          │
└──────────┬──────────┘           └──────────┬──────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                        MODEL                                 │
│  • Validations  • Associations  • Scopes  • Callbacks       │
└─────────────────────────┬───────────────────────────────────┘
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
┌─────────────────────┐       ┌─────────────────────┐
│     PRESENTER       │       │    VIEW COMPONENT   │
│  • Formatting       │       │  • Reusable UI      │
│  • Display logic    │       │  • Encapsulated     │
└──────────┬──────────┘       └──────────┬──────────┘
           │                             │
           └──────────────┬──────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       RESPONSE                               │
└─────────────────────────────────────────────────────────────┘

ASYNC FLOWS:
┌─────────────────────┐       ┌─────────────────────┐
│        JOB          │       │      CHANNEL        │
│  • Background work  │       │  • Real-time        │
│  • Queue backend    │       │  • WebSockets       │
└─────────────────────┘       └─────────────────────┘

EMAIL FLOWS:
┌─────────────────────┐
│       MAILER        │
│  • Transactional    │
│  • Notifications    │
└─────────────────────┘
```

See [layer-interactions.md](reference/layer-interactions.md) for detailed examples.

## Layer Responsibilities

| Layer | Responsibility | Should NOT contain |
|-------|---------------|-------------------|
| **Controller** | HTTP, params, response | Business logic, queries |
| **Model** | Data, validations, relations, aggregate behavior | Display logic, HTTP |
| **Service** | Cross-model orchestration, side effects, external systems | HTTP, display logic |
| **Query** | Complex database queries | Business logic |
| **Presenter** | View formatting, badges | Business logic, queries |
| **Policy** | Authorization rules | Business logic |
| **Component** | Reusable UI encapsulation | Business logic |
| **Job** | Async processing | HTTP, display logic |
| **Form** | Complex form handling | Persistence logic |
| **Mailer** | Email composition | Business logic |
| **Channel** | WebSocket communication | Business logic |

## Project Directory Structure

```
app/
├── channels/            # Action Cable channels
├── components/          # ViewComponents (UI + logic)
├── controllers/
│   └── concerns/        # Shared controller behavior
├── forms/               # Form objects
├── helpers/             # Simple view helpers (avoid)
├── jobs/                # Background jobs
├── mailers/             # Action Mailer classes
├── models/
│   └── concerns/        # Shared model behavior
├── policies/            # Pundit authorization
├── presenters/          # View formatting
├── queries/             # Complex queries
├── services/            # Cross-model orchestration and external systems
└── views/
    └── layouts/
        └── mailer.html.erb  # Email layout
```

## Core Principles

### 1. Conventional Controllers

Controllers should only:
- Authenticate/authorize
- Parse params
- Load records and call model behavior
- Render response

```ruby
# GOOD: standard Rails CRUD
class OrdersController < ApplicationController
  before_action :set_order, only: %i[ show edit update destroy ]

  def create
    @order = current_account.orders.build(order_params)

    if @order.save
      redirect_to @order, notice: t(".success")
    else
      render :new, status: :unprocessable_entity
    end
  end

  private
    def set_order
      @order = current_account.orders.find(params[:id])
    end

    def order_params
      params.expect(order: [ :name, :starts_on ])
    end
end

# BAD: Fat controller with business logic
class OrdersController < ApplicationController
  def create
    @order = Order.new(order_params)
    @order.user = current_user

    if @order.valid?
      inventory_available = @order.items.all? do |item|
        Product.find(item.product_id).inventory >= item.quantity
      end

      if inventory_available
        # ... more logic
      end
    end
  end
end
```

### 2. Rich Models, Small Collaborators

Models handle:
- Validations
- Associations
- Scopes
- Simple derived attributes
- Cohesive state transitions and aggregate-local behavior

Services handle:
- Multi-model operations
- External API calls
- Cross-aggregate orchestration
- Transactions across models

### 3. Service Return Values

Do not introduce an `ApplicationService`, interactor DSL, or shared `Result` object by default. Prefer plain return values, Active Record validations, and Rails exceptions. Add a small result value only when the caller truly needs typed success/failure handling.

```ruby
# GOOD: explicit value object when branching is useful
Result = Data.define(:success, :order, :error) do
  def success? = success
  def failure? = !success
end

class Orders::Checkout
  def call(order)
    order.with_lock do
      return Result.new(false, order, "Order is empty") if order.empty?

      order.checkout!
      Result.new(true, order, nil)
    end
  end
end
```

### 4. Multi-Tenancy by Default

All queries scoped through account:

```ruby
# GOOD: Scoped through account
def index
  @events = current_account.events.recent
end

# BAD: Unscoped query
def index
  @events = Event.where(user_id: current_user.id)
end
```

## When NOT to Abstract (Avoid Over-Engineering)

| Situation | Keep It Simple | Don't Create |
|-----------|----------------|--------------|
| Simple CRUD (< 10 lines) | Keep in controller | Service object |
| Used only once | Inline the code | Abstraction |
| Simple query with 1-2 conditions | Model scope | Query object |
| Basic text formatting | Helper method | Presenter |
| Single model form | `form_with model:` | Form object |
| Simple partial without logic | Partial | ViewComponent |

### Signs of Over-Engineering

```ruby
# OVER-ENGINEERED: Service for simple save
class Users::UpdateEmailService
  def call(user, email)
    user.update(email: email)  # Just do this in controller!
  end
end

# KEEP IT SIMPLE
class UsersController < ApplicationController
  def update
    if @user.update(user_params)
      redirect_to @user
    else
      render :edit
    end
  end
end
```

### When TO Abstract

| Signal | Action |
|--------|--------|
| Same code in 3+ places | Extract to concern/service |
| Controller action mixes HTTP with domain logic | Move cohesive behavior to the model; use a service only for orchestration |
| Model > 300 lines | Extract concerns |
| Complex conditionals | Extract to policy/service |
| Query joins 3+ tables | Extract to query object |
| Form spans multiple models | Extract to form object |

## Pattern Selection Guide

### Use Service Objects When:

- Logic spans multiple models
- External API calls needed
- Cross-aggregate transaction or side effects
- Explicit status handling materially improves clarity
- Logic reused across controllers/jobs

→ See **rails-service-object** skill for details.

### Use Query Objects When:

- Complex SQL/ActiveRecord queries
- Aggregations and statistics
- Dashboard data
- Reports

→ See **rails-query-object** skill for details.

### Use Presenters When:

- Formatting data for display
- Status badges with colors
- Currency/date formatting
- Conditional display logic

→ See **rails-presenter** skill for details.

### Use Concerns When:

- Shared validations across models
- Common scopes (e.g., `Searchable`)
- Shared callbacks (e.g., `HasUuid`)
- Keep it single-purpose!

→ See **rails-concern** skill for details.

### Use ViewComponents When:

- Reusable UI with logic
- Complex partials
- Need testable views
- Cards, tables, badges

→ See **viewcomponent-patterns** skill for details.

### Use Form Objects When:

- Multi-model forms
- Wizard/multi-step forms
- Search/filter forms
- Contact forms (no persistence)

→ See **form-object-patterns** skill for details.

### Use Policies When:

- Resource authorization
- Role-based access
- Action permissions
- Scoped collections

→ See **policy-patterns** skill for details.

## Rails 8 Specific Features

### Authentication (Built-in Generator)

```bash
bin/rails generate authentication
```

Uses `has_secure_password` with Session model, Current class, and password reset flow.

→ See **authentication-flow** skill for details.

### Background Jobs

Use the queue backend already configured by the application. Rails 8 greenfield apps may use the framework default; use Sidekiq guidance only when the repo has chosen Sidekiq or the user explicitly asks for it.

→ See **sidekiq-setup** skill for details.

### Real-time (Action Cable + Redis)

WebSocket support with Redis adapter.

→ See **action-cable-patterns** skill for details.

### Caching (Redis)

Redis-backed caching via `redis_cache_store` when Redis is part of the stack. Otherwise follow the repo's configured cache store.

→ See **caching-strategies** skill for details.

### Other Rails 8 Defaults

| Feature | Purpose |
|---------|---------|
| **Propshaft** | Asset pipeline (replaces Sprockets) |
| **Importmap** | JavaScript without bundling |
| **Kamal** | Docker deployment |
| **Thruster** | HTTP/2 proxy with caching |

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| God Model | Unrelated reasons to change | Extract concerns or collaborators by responsibility |
| Fat Controller | Domain logic in controllers | Move cohesive behavior to models; use services for orchestration |
| Callback Hell | Complex model callbacks | Use explicit call sites or services |
| Helper Soup | Massive helper modules | Use presenters/components |
| N+1 Queries | Unoptimized queries | Use `.includes()`, query objects |
| Stringly Typed | Magic strings everywhere | Use constants, enums |
| Premature Abstraction | Service for 3 lines | Keep in controller |

→ See **performance-optimization** skill for N+1 detection.

## Testing Strategy by Layer

| Layer | Test Type | Focus |
|-------|-----------|-------|
| Model | Unit | Validations, scopes, methods |
| Service | Unit | Orchestration, transactions, external-system boundaries |
| Query | Unit | Query results, tenant isolation |
| Presenter | Unit | Formatting, HTML output |
| Controller | Request | Integration, HTTP flow |
| Component | Component | Rendering, variants |
| Policy | Unit | Authorization rules |
| Form | Unit | Validations, persistence |
| System | E2E | Critical user paths |

→ See **tdd-cycle** skill for TDD workflow.

## Quick Reference

### New Feature Checklist

1. **Model** - Define data structure
2. **Policy** - Add authorization rules
3. **Service** - Create for complex logic (if needed)
4. **Query** - Add for complex queries (if needed)
5. **Controller** - Keep it thin!
6. **Form** - Use for multi-model forms (if needed)
7. **Presenter** - Format for display
8. **Component** - Build reusable UI
9. **Mailer** - Add transactional emails (if needed)
10. **Job** - Add background processing (if needed)

### Refactoring Signals

| Signal | Action |
|--------|--------|
| Model > 300 lines | Extract concern or service |
| Controller action > 15 lines | Extract service |
| View logic in helpers | Use presenter |
| Repeated query patterns | Extract query object |
| Complex partial with logic | Use ViewComponent |
| Form with multiple models | Use form object |
| Same code in 3+ places | Extract to shared module |

## Related Skills

| Category | Skills |
|----------|--------|
| **Data Layer** | rails-model-generator, rails-query-object, database-migrations |
| **Business Logic** | rails-service-object, rails-concern, form-object-patterns |
| **Presentation** | rails-presenter, viewcomponent-patterns |
| **Controllers** | rails-controller, api-patterns |
| **Auth** | authentication-flow, policy-patterns |
| **Background** | sidekiq-setup, action-mailer-patterns |
| **Real-time** | action-cable-patterns, turbo-patterns |
| **Performance** | caching-strategies, performance-optimization |
| **I18n** | i18n-patterns |
| **Testing** | tdd-cycle |

## References

- See [layer-interactions.md](reference/layer-interactions.md) for layer communication patterns
- See [service-patterns.md](reference/service-patterns.md) for service object patterns
- See [query-patterns.md](reference/query-patterns.md) for query object patterns
- See [error-handling.md](reference/error-handling.md) for error handling strategies
- See [testing-strategy.md](reference/testing-strategy.md) for comprehensive testing
