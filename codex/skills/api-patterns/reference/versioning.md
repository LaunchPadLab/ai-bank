# API Versioning for Rails

## Overview

Well-structured APIs need versioning for backwards compatibility and clear organization.

## Versioning Strategies

| Strategy | URL Example | Header Example |
|----------|-------------|----------------|
| URL Path | `/api/v1/users` | - |
| Query Param | `/api/users?version=1` | - |
| Header | `/api/users` | `Accept: application/vnd.api+json; version=1` |
| Accept Header | `/api/users` | `Accept: application/vnd.myapp.v1+json` |

**Recommended**: URL Path versioning (most common, easiest to understand)

## Quick Setup

### Routes

```ruby
# config/routes.rb
Rails.application.routes.draw do
  namespace :api do
    namespace :v1 do
      resources :users, only: [:index, :show, :create, :update, :destroy]
      resources :posts, only: [:index, :show, :create]
    end

    # v2 with changes
    namespace :v2 do
      resources :users, only: [:index, :show, :create, :update, :destroy]
    end
  end
end
```

### Directory Structure

```
app/controllers/
├── api/
│   ├── base_controller.rb      # Shared API logic
│   ├── v1/
│   │   ├── base_controller.rb  # V1 base
│   │   ├── users_controller.rb
│   │   └── posts_controller.rb
│   └── v2/
│       ├── base_controller.rb  # V2 base
│       └── users_controller.rb
```

### Base Controller

```ruby
# app/controllers/api/base_controller.rb
module Api
  class BaseController < ApplicationController
    # Skip CSRF for API requests
    skip_before_action :verify_authenticity_token

    # Respond with JSON by default
    respond_to :json

    # Handle common errors
    rescue_from ActiveRecord::RecordNotFound, with: :not_found
    rescue_from ActiveRecord::RecordInvalid, with: :unprocessable_entity
    rescue_from ActionController::ParameterMissing, with: :bad_request

    private

    def not_found(exception)
      render json: { error: exception.message }, status: :not_found
    end

    def unprocessable_entity(exception)
      render json: { errors: exception.record.errors }, status: :unprocessable_entity
    end

    def bad_request(exception)
      render json: { error: exception.message }, status: :bad_request
    end
  end
end
```

### Version Base Controller

```ruby
# app/controllers/api/v1/base_controller.rb
module Api
  module V1
    class BaseController < Api::BaseController
      # V1-specific configuration
    end
  end
end
```

### Resource Controller

```ruby
# app/controllers/api/v1/users_controller.rb
module Api
  module V1
    class UsersController < BaseController
      before_action :set_user, only: [:show, :update, :destroy]

      def index
        @users = User.page(params[:page]).per(25)
        render json: {
          data: @users,
          meta: pagination_meta(@users)
        }
      end

      def show
        render json: { data: @user }
      end

      def create
        @user = User.create!(user_params)
        render json: { data: @user }, status: :created
      end

      def update
        @user.update!(user_params)
        render json: { data: @user }
      end

      def destroy
        @user.destroy
        head :no_content
      end

      private

      def set_user
        @user = User.find(params[:id])
      end

      def user_params
        params.expect(user: [ :name, :email ])
      end

      def pagination_meta(collection)
        {
          current_page: collection.current_page,
          total_pages: collection.total_pages,
          total_count: collection.total_count
        }
      end
    end
  end
end
```

## Response Format

### Standard JSON Response

```json
{
  "data": {
    "id": 1,
    "type": "user",
    "attributes": {
      "name": "John Doe",
      "email": "john@example.com",
      "created_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

### Collection Response

```json
{
  "data": [
    { "id": 1, "type": "user", "attributes": { ... } },
    { "id": 2, "type": "user", "attributes": { ... } }
  ],
  "meta": {
    "current_page": 1,
    "total_pages": 10,
    "total_count": 100
  }
}
```

### Error Response

```json
{
  "error": "Record not found",
  "code": "not_found"
}

{
  "errors": {
    "email": ["has already been taken"],
    "name": ["can't be blank"]
  }
}
```

## Testing APIs

### Request Test Template

```ruby
# test/integration/api/v1/users_test.rb
require "test_helper"

class Api::V1::UsersTest < ActionDispatch::IntegrationTest
  setup do
    @headers = { "Accept" => "application/json", "Content-Type" => "application/json" }
    @user = users(:one)
  end

  test "GET /api/v1/users returns all users" do
    get "/api/v1/users", headers: @headers

    assert_response :ok
    assert_equal User.count, json_response["data"].size
  end

  test "GET /api/v1/users returns paginated results" do
    get "/api/v1/users", params: { page: 1 }, headers: @headers

    assert_includes json_response["meta"].keys, "current_page"
    assert_includes json_response["meta"].keys, "total_pages"
  end

  test "GET /api/v1/users/:id returns the user" do
    get "/api/v1/users/#{@user.id}", headers: @headers

    assert_response :ok
    assert_equal @user.id, json_response["data"]["id"]
  end

  test "GET /api/v1/users/:id returns 404 when not found" do
    get "/api/v1/users/999999", headers: @headers

    assert_response :not_found
  end

  test "POST /api/v1/users creates a user" do
    valid_params = { user: { name: "Test", email: "test@example.com" } }

    assert_difference "User.count", 1 do
      post "/api/v1/users", params: valid_params.to_json, headers: @headers
    end

    assert_response :created
  end

  test "POST /api/v1/users returns validation errors for invalid params" do
    invalid_params = { user: { name: "", email: "" } }

    post "/api/v1/users", params: invalid_params.to_json, headers: @headers

    assert_response :unprocessable_entity
    assert json_response["errors"].present?
  end

  private

  def json_response
    JSON.parse(response.body)
  end
end
```

## API Authentication

### Token-Based Auth

```ruby
# app/controllers/api/base_controller.rb
module Api
  class BaseController < ApplicationController
    before_action :authenticate_api_user!

    private

    def authenticate_api_user!
      token = request.headers['Authorization']&.split(' ')&.last
      @current_api_user = User.find_by(api_token: token)

      render json: { error: 'Unauthorized' }, status: :unauthorized unless @current_api_user
    end

    def current_api_user
      @current_api_user
    end
  end
end
```

### JWT Authentication

```ruby
# Using jwt gem
def authenticate_api_user!
  token = request.headers['Authorization']&.split(' ')&.last
  return unauthorized unless token

  payload = JWT.decode(token, Rails.application.secret_key_base).first
  @current_api_user = User.find(payload['user_id'])
rescue JWT::DecodeError
  unauthorized
end

def unauthorized
  render json: { error: 'Unauthorized' }, status: :unauthorized
end
```

## Workflow Checklist

```
API Implementation:
- [ ] Define routes in namespace
- [ ] Create base controller with error handling
- [ ] Create version-specific base controller
- [ ] Create resource controller
- [ ] Add authentication (if needed)
- [ ] Write request/integration tests
- [ ] Document API endpoints
```
