---
name: hipaa-security
description: HIPAA security safeguards and authentication requirements
---
# HIPAA Security Safeguards

Implement these required security safeguards for HIPAA compliance.

## Authentication Requirements

### Multi-Factor Authentication (MFA)
- MFA is REQUIRED for all users accessing PHI
- Support authenticator apps (TOTP) as primary MFA method
- SMS-based MFA is acceptable but less secure
- Biometric authentication (fingerprint, face) for mobile apps

### Password Requirements
- Minimum 12 characters
- Require complexity (uppercase, lowercase, numbers, special characters)
- Password history enforcement (prevent reuse of last 12 passwords)
- Maximum password age of 90 days for staff accounts
- Account lockout after 5 failed attempts

### Session Security
```ruby
# config/initializers/session_store.rb
Rails.application.config.session_store :cookie_store,
  key: '_prospectus_session',
  secure: Rails.env.production?,
  httponly: true,
  same_site: :strict,
  expire_after: 30.minutes  # HIPAA requires reasonable timeout
```

## Access Control Patterns

### Role-Based Access Control (RBAC)
```ruby
# Example Pundit policy for patient records
class PatientPolicy < ApplicationPolicy
  def show?
    case user.role
    when 'patient'
      record.user_id == user.id  # Patients see only their own records
    when 'provider'
      user.assigned_patients.include?(record)  # Providers see assigned patients
    when 'client_admin'
      user.organization.patients.include?(record)  # Client admins see org patients
    else
      false
    end
  end
  
  def update?
    user.role == 'provider' && user.assigned_patients.include?(record)
  end
end
```

### Minimum Necessary Standard
Only expose the minimum PHI required for the user's function:
```ruby
# Different serializers based on role
class PatientSerializer
  def self.for_role(patient, role)
    case role
    when 'provider'
      FullPatientSerializer.new(patient)
    when 'scheduler'
      SchedulingPatientSerializer.new(patient)  # Name, DOB, contact only
    when 'billing'
      BillingPatientSerializer.new(patient)  # Insurance info only
    end
  end
end
```

## Audit Logging Implementation

### Comprehensive Audit Trail
```ruby
# app/models/audit_log.rb
class AuditLog < ApplicationRecord
  # Required fields for HIPAA compliance
  # user_id: Who performed the action
  # action: What action was performed (view, create, update, delete, export, print)
  # resource_type: Type of resource accessed
  # resource_id: ID of specific resource
  # ip_address: Origin of request
  # user_agent: Browser/client info
  # timestamp: When it occurred (with timezone)
  # changes: For updates, what changed (sanitized)
  # reason: Optional justification for access
  
  validates :user_id, :action, :resource_type, :ip_address, presence: true
  
  # Audit logs must be immutable - no updates or deletes
  before_update { raise ActiveRecord::ReadOnlyRecord }
  before_destroy { raise ActiveRecord::ReadOnlyRecord }
  
  # Retention: HIPAA requires 6 years minimum
  scope :expired, -> { where('created_at < ?', 7.years.ago) }
end
```

### Automatic Audit Logging Concern
```ruby
# app/controllers/concerns/auditable.rb
module Auditable
  extend ActiveSupport::Concern
  
  included do
    after_action :record_audit_log, if: :phi_resource?
  end
  
  private
  
  def record_audit_log
    AuditLog.create!(
      user_id: current_user&.id,
      action: audit_action,
      resource_type: controller_name.classify,
      resource_id: resource_id_for_audit,
      ip_address: request.remote_ip,
      user_agent: request.user_agent,
      request_id: request.request_id
    )
  end
  
  def audit_action
    case action_name
    when 'show', 'index' then 'view'
    when 'create' then 'create'
    when 'update' then 'update'
    when 'destroy' then 'delete'
    else action_name
    end
  end
end
```

## Encryption Standards

### Application-Level Encryption for Sensitive Fields
```ruby
# app/models/patient.rb
class Patient < ApplicationRecord
  # Use Rails 7+ encryption for sensitive fields
  encrypts :social_security_number, deterministic: true  # Allows querying
  encrypts :medical_notes  # Non-deterministic for maximum security
  encrypts :diagnosis_codes
  
  # Or use attr_encrypted gem for more control
  # attr_encrypted :ssn, key: ENV['ENCRYPTION_KEY']
end
```

### Key Management
- NEVER store encryption keys in source code
- Use environment variables or secure key management service
- Rotate encryption keys annually
- Document key rotation procedures

## Security Headers
```ruby
# config/initializers/security_headers.rb
Rails.application.config.action_dispatch.default_headers = {
  'X-Frame-Options' => 'DENY',
  'X-Content-Type-Options' => 'nosniff',
  'X-XSS-Protection' => '1; mode=block',
  'Strict-Transport-Security' => 'max-age=31536000; includeSubDomains',
  'Content-Security-Policy' => "default-src 'self'; script-src 'self'"
}
```

## Failed Login Handling
```ruby
# Track and respond to failed login attempts
class SessionsController < ApplicationController
  def create
    user = User.find_by(email: params[:email])
    
    if user&.locked?
      AuditLog.record_security_event(:login_attempt_locked_account, params[:email], request)
      flash[:alert] = "Account is locked. Contact support."
      render :new
    elsif user&.authenticate(params[:password])
      user.reset_failed_attempts!
      AuditLog.record_security_event(:login_success, user, request)
      # ... create session
    else
      user&.record_failed_attempt!
      AuditLog.record_security_event(:login_failure, params[:email], request)
      # Don't reveal if user exists
      flash[:alert] = "Invalid email or password"
      render :new
    end
  end
end
```

## Secure API Design
```ruby
# All API endpoints accessing PHI must:
class Api::V1::PatientsController < Api::BaseController
  before_action :authenticate_api_user!      # 1. Authenticate
  before_action :verify_mfa_completed!       # 2. Verify MFA
  before_action :authorize_patient_access!   # 3. Authorize
  after_action :audit_api_access            # 4. Audit
  
  # Rate limiting to prevent data harvesting
  rate_limit to: 100, within: 1.minute, only: [:index, :show]
end
```

## Security Incident Response

### Breach Detection Logging
```ruby
# Log potential security incidents for review
class SecurityMonitor
  SUSPICIOUS_PATTERNS = [
    :multiple_failed_logins,
    :unusual_access_hours,
    :bulk_record_access,
    :access_from_new_location,
    :export_large_dataset
  ]
  
  def self.check(user, action, context)
    SUSPICIOUS_PATTERNS.each do |pattern|
      if send("#{pattern}?", user, action, context)
        SecurityIncident.create!(
          pattern: pattern,
          user: user,
          details: context,
          severity: calculate_severity(pattern)
        )
        notify_security_team(pattern, user, context)
      end
    end
  end
end
```

## References
- [Medical Web Experts - HIPAA Security](https://www.medicalwebexperts.com/blog/how-to-make-a-hipaa-compliant-healthcare-app/)
- [HIPAA Security Rule Technical Safeguards](https://www.hhs.gov/hipaa/for-professionals/security/guidance/index.html)
