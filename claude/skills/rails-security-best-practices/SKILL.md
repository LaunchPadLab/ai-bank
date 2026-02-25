---
name: rails-security-best-practices
description: Enforces Rails security best practices across the codebase. Use when creating controllers, models, API endpoints, handling user input, file uploads, authentication, authorization, session management, or configuring production environments. Also use during code reviews to check for SQL injection, XSS, CSRF vulnerabilities, hard-coded secrets, or missing access controls.
allowed-tools: Read, Write, Edit, Bash(bundle exec rspec:*), Glob, Grep
---

# Rails Security Best Practices

## When to Use
Apply this skill when:
- Creating new Rails controllers, models, or API endpoints
- Reviewing code for security vulnerabilities
- Setting up authentication/authorization
- Handling user input, file uploads, or sensitive data
- Configuring production environments

## Core Principles

**Assume all user input is hostile. Enforce security in code, not just UI.**

---

## 1. Secrets & Configuration

- **Never** hard-code secrets in source code
- Use `rails credentials:edit` or ENV vars via the deployment platform
- Each environment (dev, staging, prod) gets its own keys
- Run `bundle exec bundle-audit check --update` in CI regularly

```ruby
# config/database.yml
production:
  adapter: postgresql
  url: <%= ENV.fetch("DATABASE_URL") %>
```

## 2. Authentication & Authorization

- Use proven gems: **Devise**, **Sorcery**, or Rails 8 built-in `has_secure_password`
- Enforce strong passwords, session expiration, and re-auth for sensitive actions
- Centralize authorization with **Pundit** or **CanCanCan** — never rely on UI hiding alone

```ruby
# Pundit policy
class ProjectPolicy < ApplicationPolicy
  def update?
    user.admin? || record.owner_id == user.id
  end
end
```

**Anti-pattern:** Hiding buttons in views without enforcing permissions in controllers/policies. Attackers hit endpoints directly.

## 3. Injection & XSS Prevention

### SQL Injection
```ruby
# SAFE — parameterized
User.where(email: params[:email])

# UNSAFE — string interpolation
User.where("email = '#{params[:email]}'")
```

### XSS
- Rails ERB escapes output by default — **never** use `raw` or `.html_safe` on user input
- Sanitize rich text explicitly:

```ruby
ActionController::Base.helpers.sanitize(
  params[:content],
  tags: %w[p b i strong em a ul ol li],
  attributes: %w[href]
)
```

## 4. CSRF & Session Hardening

```ruby
# ApplicationController — keep this enabled
protect_from_forgery with: :exception
```

```ruby
# config/initializers/session_store.rb
Rails.application.config.session_store :cookie_store,
  key: "_myapp_session",
  secure: Rails.env.production?,
  httponly: true,
  same_site: :lax
```

- For JSON APIs: use separate API controllers with token-based auth instead of CSRF tokens

## 5. HTTPS & Security Headers

```ruby
# config/environments/production.rb
config.force_ssl = true
```

```ruby
# config/initializers/content_security_policy.rb
Rails.application.configure do
  config.content_security_policy do |policy|
    policy.default_src :self
    policy.script_src  :self, :https
    policy.style_src   :self, :https, :unsafe_inline
    policy.img_src     :self, :https, :data
  end
end
```

- Set HSTS, `X-Frame-Options`, and `X-Content-Type-Options: nosniff` via middleware or reverse proxy

## 6. Data & File Upload Protection

### Encrypt sensitive attributes (Rails 7+)
```ruby
class User < ApplicationRecord
  encrypts :ssn, :personal_token
end
```

### Validate uploads strictly
```ruby
class Document < ApplicationRecord
  has_one_attached :file

  validate :acceptable_file

  def acceptable_file
    return unless file.attached?
    errors.add(:file, "is too big") unless file.byte_size <= 10.megabytes
    errors.add(:file, "must be a PDF") unless file.content_type.in?(%w[application/pdf])
  end
end
```

- Store uploads on S3/GCS, **not** the app server's public directory
- Serve via signed URLs; never execute uploaded content

## 7. Logging & Rate Limiting

### Filter sensitive params
```ruby
# config/initializers/filter_parameter_logging.rb
Rails.application.config.filter_parameters += %i[
  password password_confirmation token api_key ssn
]
```

### Throttle abuse with Rack::Attack
```ruby
Rack::Attack.throttle("logins/ip", limit: 10, period: 60.seconds) do |req|
  req.ip if req.path == "/users/sign_in" && req.post?
end
```

- Log auth failures, permission denials, and suspicious patterns
- Integrate with monitoring (Sentry, Datadog, etc.)

## 8. CI/CD Security Checklist

- [ ] `bundle-audit` runs on every merge
- [ ] Secret scanning enabled (e.g., GitGuardian, GitHub secret scanning)
- [ ] Builds fail on critical vulnerabilities
- [ ] Static analysis lints for unsafe patterns (`brakeman`)
- [ ] Code reviews explicitly ask: "What if this input is malicious?" and "What if an unauthorized user calls this endpoint?"

## Quick Reference: Common Mistakes

| Mistake | Fix |
|---|---|
| `User.where("email = '#{params[:email]}'")` | `User.where(email: params[:email])` |
| `<%= raw @user_content %>` | `<%= @user_content %>` (auto-escaped) |
| Checking permissions only in views | Enforce via Pundit/CanCanCan policies |
| Hard-coded API keys in source | `rails credentials:edit` or ENV vars |
| Disabled CSRF protection | Keep `protect_from_forgery` enabled |
| Uploads in `public/` directory | Use Active Storage + S3 with signed URLs |
| Unfiltered log output | Add sensitive fields to `filter_parameters` |