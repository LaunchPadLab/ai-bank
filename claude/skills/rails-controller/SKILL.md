---
name: rails-controller
description: Creates Rails controllers with TDD approach - controller test first, then implementation. Use when creating new controllers, adding controller actions, implementing CRUD operations, or when user mentions controllers, routes, or API endpoints.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Rails Controller Generator (TDD)

Creates RESTful controllers following project conventions with controller tests first.

## Quick Start

1. Write failing controller test in `test/controllers/`
2. Run test to confirm RED
3. Implement controller action
4. Run test to confirm GREEN
5. Refactor if needed

## Project Conventions

This project uses:
- **Pundit** for authorization (`authorize @resource`, `policy_scope(Model)`)
- **Pagy** for pagination
- **Presenters** for view formatting
- **Multi-tenancy** via `current_account`
- **Turbo Stream** responses for dynamic updates

## TDD Workflow

### Step 1: Create Controller Test (RED)

```ruby
# test/controllers/[resources]_controller_test.rb
require "test_helper"

class ResourcesControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:one)
    @other_user = users(:two)
    sign_in @user
  end

  test "GET /resources returns http success" do
    get resources_path
    assert_response :success
  end

  test "GET /resources shows only current_user's resources (multi-tenant)" do
    resource = resources(:one)        # belongs to @user.account
    other_resource = resources(:two)  # belongs to @other_user.account

    get resources_path

    assert_includes response.body, resource.name
    assert_not_includes response.body, other_resource.name
  end

  test "GET /resources/:id returns http success" do
    resource = resources(:one)
    get resource_path(resource)
    assert_response :success
  end

  test "POST /resources creates a new resource" do
    assert_difference("Resource.count", 1) do
      post resources_path, params: { resource: { name: "New Resource", field1: "value" } }
    end
  end

  test "POST /resources assigns to current_account" do
    post resources_path, params: { resource: { name: "New Resource", field1: "value" } }
    assert_equal @user.account, Resource.last.account
  end

  test "GET /resources/:id returns 404 for unauthorized access" do
    other_resource = resources(:two)  # belongs to @other_user.account
    get resource_path(other_resource)
    assert_response :not_found
  end
end
```

### Step 2: Run Test (Confirm RED)

```bash
bin/rails test test/controllers/resources_controller_test.rb
```

### Step 3: Implement Controller (GREEN)

```ruby
# app/controllers/[resources]_controller.rb
class [Resources]Controller < ApplicationController
  before_action :set_[resource], only: [:show, :edit, :update, :destroy]

  def index
    authorize [Resource], :index?
    @pagy, resources = pagy(policy_scope([Resource]).order(created_at: :desc))
    @[resources] = resources.map { |r| [Resource]Presenter.new(r) }
  end

  def show
    authorize @[resource]
    @[resource] = [Resource]Presenter.new(@[resource])
  end

  def new
    @[resource] = current_account.[resources].build
    authorize @[resource]
  end

  def create
    @[resource] = current_account.[resources].build([resource]_params)
    authorize @[resource]

    if @[resource].save
      redirect_to [resources]_path, notice: "[Resource] created successfully"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    authorize @[resource]
  end

  def update
    authorize @[resource]

    if @[resource].update([resource]_params)
      redirect_to @[resource], notice: "[Resource] updated successfully"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    authorize @[resource]
    @[resource].destroy
    redirect_to [resources]_path, notice: "[Resource] deleted successfully"
  end

  private

  def set_[resource]
    @[resource] = policy_scope([Resource]).find(params[:id])
  end

  def [resource]_params
    params.expect(resource: [ :name, :field1, :field2 ])
  end
end
```

### Step 4: Run Test (Confirm GREEN)

```bash
bin/rails test test/controllers/resources_controller_test.rb
```

## Namespaced Controllers

For nested routes like `settings/accounts`:

```ruby
# app/controllers/settings/accounts_controller.rb
module Settings
  class AccountsController < ApplicationController
    before_action :set_account

    def show
      authorize @account
    end

    private

    def set_account
      @account = current_account
    end
  end
end
```

## Turbo Stream Response Pattern

```ruby
def create
  @resource = current_account.resources.build(resource_params)
  authorize @resource

  if @resource.save
    respond_to do |format|
      format.html { redirect_to resources_path, notice: "Created" }
      format.turbo_stream do
        flash.now[:notice] = "Created"
        @pagy, @resources = pagy(policy_scope(Resource).order(created_at: :desc))
        render turbo_stream: [
          turbo_stream.replace("resources-list", partial: "resources/list"),
          turbo_stream.update("modal", "")
        ]
      end
    end
  else
    render :new, status: :unprocessable_entity
  end
end
```

## Checklist

- [ ] Controller test written first (RED)
- [ ] Multi-tenant isolation tested
- [ ] Authorization tested (404 for unauthorized)
- [ ] Controller uses `authorize` on every action
- [ ] Controller uses `policy_scope` for queries
- [ ] Presenter wraps models for views
- [ ] Strong parameters defined
- [ ] All tests GREEN

## Additional Resources

- [domain-patterns.md](reference/domain-patterns.md) – CRUD philosophy, state change controllers, routing patterns, resource thinking, respond_to patterns, and controller concerns
