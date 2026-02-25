# Rails Setup for Hotwire Native Authentication

## Authentication Concern

The key change from standard Rails authentication is using `cookies.signed.permanent` instead of session-only cookies. This ensures the cookie persists after the native app is closed.

```ruby
# app/controllers/concerns/authentication.rb
module Authentication
  extend ActiveSupport::Concern

  included do
    before_action :require_authentication
    helper_method :authenticated?
  end

  class_methods do
    def allow_unauthenticated_access(**options)
      skip_before_action :require_authentication, **options
    end
  end

  private

  def authenticated?
    Current.session.present?
  end

  def require_authentication
    resume_session || request_authentication
  end

  def resume_session
    if session = find_session_by_cookie
      Current.session = session
    end
  end

  def find_session_by_cookie
    if id = cookies.signed[:session_id]
      Session.find_by(id: id)
    end
  end

  def request_authentication
    session[:return_to_after_authenticating] = request.url
    redirect_to new_session_path
  end

  def after_authentication_url
    session.delete(:return_to_after_authenticating) || root_url
  end

  def start_new_session_for(user)
    session = user.sessions.create!(
      ip_address: request.remote_ip,
      user_agent: request.user_agent
    )
    Current.session = session
    cookies.signed.permanent[:session_id] = {
      value: session.id, httponly: true, same_site: :lax
    }
  end

  def terminate_session
    Current.session&.destroy
    cookies.delete(:session_id)
  end
end
```

## Application Controller

```ruby
# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  include Authentication
end
```

## Sessions Controller

```ruby
# app/controllers/sessions_controller.rb
class SessionsController < ApplicationController
  allow_unauthenticated_access only: %i[new create]

  def new
  end

  def create
    if user = User.authenticate_by(
      email_address: params[:email_address],
      password: params[:password]
    )
      start_new_session_for(user)
      redirect_to after_authentication_url
    else
      flash.now[:alert] = "Try another email address or password."
      render :new, status: :unprocessable_entity
    end
  end

  def destroy
    terminate_session
    redirect_to new_session_path
  end
end
```

## Application Layout

The layout must include:
1. The `<meta>` tag with authentication bridge controller
2. Conditional native CSS loading
3. Standard Turbo/Stimulus setup

```erb
<%# app/views/layouts/application.html.erb %>
<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <%= csrf_meta_tags %>
    <%= csp_meta_tag %>
    <%= stylesheet_link_tag "application" %>
    <% if hotwire_native_app? %>
      <%= stylesheet_link_tag "native" %>
    <% end %>
    <%= javascript_importmap_tags %>
  </head>

  <body>
    <meta data-controller="bridge--authentication"
      data-bridge-authenticated="<%= authenticated? %>">

    <%= render "shared/flash" %>
    <%= yield %>
  </body>
</html>
```

## Bridge Stimulus Controller

```javascript
// app/javascript/controllers/bridge/authentication_controller.js
import { BridgeComponent } from "@hotwired/hotwire-native-bridge"

export default class extends BridgeComponent {
  static component = "authentication"

  connect() {
    const authenticated = this.bridgeElement
      .bridgeAttribute("authenticated") === "true"

    if (authenticated) {
      this.send("signIn")
    } else {
      this.send("signOut")
    }
  }
}
```

## Importmap Configuration

```ruby
# config/importmap.rb
pin "application"
pin "@hotwired/turbo-rails", to: "turbo.min.js"
pin "@hotwired/stimulus", to: "@hotwired--stimulus.js"
pin "@hotwired/stimulus-loading", to: "stimulus-loading.js"
pin "@hotwired/hotwire-native-bridge", to: "@hotwired--hotwire-native-bridge.js"
pin_all_from "app/javascript/controllers", under: "controllers"
```

Install the bridge package:

```bash
bin/importmap pin @hotwired/hotwire-native-bridge
```

## Native CSS

```css
/* app/assets/stylesheets/native.css */
.d-hotwire-native-none {
  display: none;
}
```

Use `.d-hotwire-native-none` on elements that should only appear in web browsers (headers, breadcrumbs, etc.):

```erb
<%# app/views/shared/_header.html.erb %>
<header class="d-hotwire-native-none">
  <nav>
    <%= link_to "Home", root_path %>
  </nav>
</header>
```

## Path Configuration Controller

```ruby
# app/controllers/configurations_controller.rb
class ConfigurationsController < ApplicationController
  allow_unauthenticated_access

  def ios
    render json: {
      settings: {},
      rules: [
        {
          patterns: ["/new$", "/edit$"],
          properties: { context: "modal" }
        },
        {
          patterns: ["/session/new"],
          properties: { context: "default" }
        }
      ]
    }
  end

  def android
    render json: {
      settings: {},
      rules: [
        {
          patterns: [".*"],
          properties: {
            context: "default",
            pull_to_refresh_enabled: true
          }
        },
        {
          patterns: ["/new$", "/edit$"],
          properties: { context: "modal" }
        },
        {
          patterns: ["/session/new"],
          properties: { context: "default" }
        }
      ]
    }
  end
end
```

## Routes

```ruby
# config/routes.rb
Rails.application.routes.draw do
  resource :session
  resource :profile, only: :show
  resources :posts

  resource :configuration, only: [], constraints: { format: :json } do
    get :ios, on: :member
    get :android, on: :member
  end

  root "posts#index"
end
```

## Models

```ruby
# app/models/user.rb
class User < ApplicationRecord
  has_secure_password
  has_many :sessions, dependent: :destroy

  normalizes :email_address, with: -> { _1.strip.downcase }
end

# app/models/session.rb
class Session < ApplicationRecord
  belongs_to :user
end

# app/models/current.rb
class Current < ActiveSupport::CurrentAttributes
  attribute :session
  delegate :user, to: :session, allow_nil: true
end
```

## Sign-In View

```erb
<%# app/views/sessions/new.html.erb %>
<header class="d-hotwire-native-none">
  <h1>Sign In</h1>
</header>

<%= form_with url: session_path, data: { turbo_action: "replace" } do |form| %>
  <div>
    <%= form.label :email_address %>
    <%= form.email_field :email_address, autofocus: true, autocomplete: "email" %>
  </div>

  <div>
    <%= form.label :password %>
    <%= form.password_field :password, autocomplete: "current-password" %>
  </div>

  <%= form.submit "Sign in" %>
<% end %>
```

The `data: { turbo_action: "replace" }` ensures Turbo replaces the current page rather than pushing onto the navigation stack after sign-in.

## Gemfile Dependencies

```ruby
gem "rails", "~> 8.0"
gem "turbo-rails"
gem "stimulus-rails"
gem "importmap-rails"
gem "bcrypt", "~> 3.1.7"  # For has_secure_password
```

## Database Schema

```ruby
# Users
create_table :users do |t|
  t.string :email_address, null: false
  t.string :password_digest, null: false
  t.timestamps
end
add_index :users, :email_address, unique: true

# Sessions
create_table :sessions do |t|
  t.references :user, null: false, foreign_key: true
  t.string :ip_address
  t.string :user_agent
  t.timestamps
end
```
