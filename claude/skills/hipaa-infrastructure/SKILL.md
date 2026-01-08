---
name: hipaa-infrastructure
description: HIPAA-compliant infrastructure and hosting requirements for Heroku Shield
---
# HIPAA Infrastructure & Heroku Shield

This application runs on Heroku Private Shield, which provides HIPAA-eligible infrastructure. Follow these rules to maintain compliance.

## Heroku Shield Requirements

### Required Shield Add-ons
Only use Shield-compatible add-ons that sign BAAs:
- **Heroku Postgres Shield** - For all PHI data
- **Heroku Redis Shield** - For sessions/caching (if caching PHI)
- **Heroku Shield Private Spaces** - Isolated network environment

### Configuration Requirements
```yaml
# Procfile
web: bundle exec puma -C config/puma.rb
worker: bundle exec sidekiq -C config/sidekiq.yml
release: bundle exec rails db:migrate
```

## Database Configuration

### PostgreSQL Shield Settings
```ruby
# config/database.yml
production:
  adapter: postgresql
  encoding: unicode
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
  url: <%= ENV['DATABASE_URL'] %>
  # SSL is REQUIRED for Shield
  sslmode: require
  # Connection timeout
  connect_timeout: 5
```

## Redis Shield Configuration

### Session Storage (Recommended for HIPAA)
```ruby
# config/initializers/session_store.rb
if Rails.env.production?
  Rails.application.config.session_store :redis_store,
    servers: [ENV['REDIS_URL']],
    expire_after: 30.minutes,
    key: '_prospectus_session',
    secure: true,
    httponly: true,
    same_site: :strict
end
```

### Redis for Sidekiq
```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  config.redis = {
    url: ENV['REDIS_URL'],
    ssl_params: { verify_mode: OpenSSL::SSL::VERIFY_NONE }  # Heroku Redis uses self-signed certs
  }
end

Sidekiq.configure_client do |config|
  config.redis = {
    url: ENV['REDIS_URL'],
    ssl_params: { verify_mode: OpenSSL::SSL::VERIFY_NONE }
  }
end
```

## Environment Variables

### Required Security Config
```bash
# Never commit these - set via Heroku config
RAILS_ENV=production
SECRET_KEY_BASE=<generated-secure-key>
ENCRYPTION_KEY=<for-application-level-encryption>
DATABASE_URL=<heroku-provides-this>
REDIS_URL=<heroku-provides-this>

# Force SSL
FORCE_SSL=true

# Session settings
SESSION_TIMEOUT_MINUTES=30

# Audit settings
AUDIT_LOG_ENABLED=true
```

### Never Log These
```ruby
# config/initializers/filter_parameter_logging.rb
Rails.application.config.filter_parameters += [
  :password, :password_confirmation,
  :ssn, :social_security_number,
  :dob, :date_of_birth,
  :mrn, :medical_record_number,
  :insurance_id, :health_plan_id,
  :credit_card, :cvv,
  :token, :secret, :api_key,
  :diagnosis, :treatment, :medication
]
```

## SSL/TLS Requirements

### Force SSL in Production
```ruby
# config/environments/production.rb
config.force_ssl = true
config.ssl_options = {
  hsts: { 
    expires: 1.year, 
    subdomains: true, 
    preload: true 
  },
  redirect: {
    exclude: ->(request) { request.path.start_with?('/health') }
  }
}
```

## Logging Configuration

### Production Logging (PHI-Safe)
```ruby
# config/environments/production.rb
config.log_level = :info

# Use tagged logging for traceability
config.log_tags = [:request_id, :remote_ip]

# Custom log formatter that filters PHI
config.logger = ActiveSupport::Logger.new(STDOUT)
config.logger.formatter = HipaaLogFormatter.new

# Silence asset logging
config.assets.quiet = true
```

### HIPAA-Safe Log Formatter
```ruby
# lib/hipaa_log_formatter.rb
class HipaaLogFormatter < Logger::Formatter
  PHI_PATTERNS = [
    /\b\d{3}[-.]?\d{2}[-.]?\d{4}\b/,  # SSN
    /\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b/  # Dates
  ]
  
  def call(severity, time, progname, msg)
    sanitized_msg = sanitize_phi(msg.to_s)
    "#{time.iso8601} #{severity} #{sanitized_msg}\n"
  end
  
  private
  
  def sanitize_phi(message)
    PHI_PATTERNS.reduce(message) do |msg, pattern|
      msg.gsub(pattern, '[REDACTED]')
    end
  end
end
```

## Health Checks (Exclude from SSL redirect)

```ruby
# config/routes.rb
Rails.application.routes.draw do
  # Health check endpoint for Heroku/load balancer
  get '/health', to: 'health#show'
end

# app/controllers/health_controller.rb
class HealthController < ApplicationController
  skip_before_action :authenticate_user!
  
  def show
    # Check critical services
    checks = {
      database: database_healthy?,
      redis: redis_healthy?,
      # Don't expose PHI in health check
    }
    
    if checks.values.all?
      render json: { status: 'ok', checks: checks }, status: :ok
    else
      render json: { status: 'unhealthy', checks: checks }, status: :service_unavailable
    end
  end
  
  private
  
  def database_healthy?
    ActiveRecord::Base.connection.execute('SELECT 1')
    true
  rescue
    false
  end
  
  def redis_healthy?
    Redis.current.ping == 'PONG'
  rescue
    false
  end
end
```

## Backup & Disaster Recovery

### Database Backups
- Heroku Shield provides automated encrypted backups
- Enable continuous protection (point-in-time recovery)
- Test restore procedures regularly
- Document backup verification in compliance records

```bash
# Heroku Shield backup commands
heroku pg:backups:schedules --app your-app
heroku pg:backups:capture --app your-app
heroku pg:backups:url --app your-app
```

## Network Security

### Private Spaces Configuration
- All dynos run in isolated Private Space
- Configure internal routing for service-to-service communication
- Use private endpoints for database connections
- Enable Shield Private Space logging

### IP Allowlisting (if required)
```ruby
# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  before_action :verify_ip_allowlist, if: :admin_area?
  
  private
  
  def verify_ip_allowlist
    allowed_ips = ENV.fetch('ADMIN_ALLOWED_IPS', '').split(',')
    unless allowed_ips.empty? || allowed_ips.include?(request.remote_ip)
      render plain: 'Forbidden', status: :forbidden
    end
  end
end
```

## Third-Party Service Checklist

Before integrating any service, verify:
- [ ] Service offers HIPAA-compliant tier
- [ ] Business Associate Agreement (BAA) is signed
- [ ] Data is encrypted in transit and at rest
- [ ] Service provides audit logs
- [ ] Incident notification procedures documented

### Common HIPAA-Compliant Services
- Email: Paubox, LuxSci, Virtru
- SMS: Twilio (with BAA), Bandwidth
- Video: Zoom for Healthcare, Doxy.me
- Analytics: None should receive PHI (use de-identified data only)

## References
- [Heroku Shield Compliance](https://www.heroku.com/shield)
- [Medical Web Experts - HIPAA-Compliant Cloud Hosting](https://www.medicalwebexperts.com/blog/how-to-make-a-hipaa-compliant-healthcare-app/)
