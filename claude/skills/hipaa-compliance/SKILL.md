---
name: hipaa-compliance
description: Core HIPAA compliance rules for healthcare app development
---
# HIPAA Compliance Rules

This is a HIPAA-compliant healthcare application. All code must be written with patient privacy and data security as the highest priority. HIPAA compliance must be baked in from the start, not retrofitted later.

## The 18 ePHI Identifiers

Protected Health Information (PHI) includes any of these identifiers when combined with health data:

1. Names
2. Geographic data smaller than state (address, city, zip code)
3. All date elements except year (birth date, admission date, discharge date, death date)
4. Phone numbers
5. Fax numbers
6. Email addresses
7. Social Security numbers
8. Medical record numbers
9. Health plan beneficiary numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers and serial numbers
13. Device identifiers and serial numbers
14. Web URLs
15. IP addresses
16. Biometric identifiers (fingerprints, voiceprints)
17. Full-face photographs
18. Any other unique identifying number or code

## Critical Rules

### 1. NEVER Store PHI on Client Devices
- All PHI must be stored server-side in HIPAA-compliant infrastructure
- Mobile/web clients should only cache temporary tokens or session data
- Never store identifiable health data in localStorage, sessionStorage, or cookies
- Use secure API calls to fetch PHI on-demand

### 2. NEVER Include PHI in Notifications
- Push notifications, SMS, and email alerts must be generic
- BAD: "Your dermatology appointment is tomorrow at 3pm"
- GOOD: "You have a new message in your secure portal"
- BAD: "Your lab results for diabetes test are ready"
- GOOD: "New information is available. Log in to view."

### 3. Audit Logging is Mandatory
Every access to PHI must be logged with:
- WHO accessed the data (user ID, role)
- WHAT data was accessed (record type, identifiers)
- WHEN it was accessed (timestamp with timezone)
- WHERE the access originated (IP address, device info)
- WHY/HOW it was accessed (action type: view, edit, export, delete)

### 4. Encryption Requirements
- All PHI must be encrypted at rest (AES-256 minimum)
- All PHI must be encrypted in transit (TLS 1.2+ required)
- Database columns containing PHI should use application-level encryption
- Encryption keys must be managed securely (never in source code)

### 5. Access Control (Role-Based)
- Implement strict Role-Based Access Control (RBAC)
- Users should only access the minimum PHI necessary for their role
- Provider Portal: Full patient records for assigned patients only
- Patient Portal: Own records only
- Client Portal: Aggregate/de-identified data or authorized patient data only

### 6. Session Management
- Implement automatic session timeouts (15-30 minutes of inactivity)
- Require re-authentication for sensitive operations
- Log all session events (login, logout, timeout, failed attempts)
- Invalidate sessions on password change

## Code Patterns

### Audit Logging Pattern
```ruby
# Always wrap PHI access in audit logging
AuditLog.record(
  user: current_user,
  action: :view,
  resource_type: 'Patient',
  resource_id: patient.id,
  ip_address: request.remote_ip,
  user_agent: request.user_agent
)
```

### PHI Access Pattern
```ruby
# Always check authorization before PHI access
class PatientRecordsController < ApplicationController
  before_action :authenticate_user!
  before_action :authorize_patient_access!
  after_action :audit_access
  
  private
  
  def authorize_patient_access!
    authorize @patient, :show?
  end
  
  def audit_access
    AuditLog.record_access(current_user, @patient, action_name)
  end
end
```

### Safe Notification Pattern
```ruby
# NEVER include PHI in notification content
class AppointmentNotificationJob < ApplicationJob
  def perform(appointment_id)
    # BAD - includes PHI
    # message = "Reminder: #{appointment.patient.name} has appointment with Dr. #{appointment.provider.name}"
    
    # GOOD - generic message
    message = "You have an upcoming appointment. Log in to view details."
    
    NotificationService.send(
      user_id: appointment.patient.user_id,
      message: message,
      # Deep link to authenticated portal, not direct to PHI
      action_url: portal_appointments_path
    )
  end
end
```

## Database Considerations

### Sensitive Columns
Never log or expose these columns in error messages:
- social_security_number
- date_of_birth (full date)
- medical_record_number
- Any diagnosis or treatment fields
- Any fields containing the 18 identifiers

### Query Logging
- Disable query logging in production for tables containing PHI
- Use parameter filtering for sensitive fields in logs:
```ruby
# config/initializers/filter_parameter_logging.rb
Rails.application.config.filter_parameters += [
  :ssn, :social_security_number, :date_of_birth, :dob,
  :medical_record_number, :mrn, :diagnosis, :treatment,
  :health_plan_id, :insurance_id, :phone, :email, :address
]
```

## Testing Requirements

- All PHI access points must have authorization tests
- All audit logging must be verified in tests
- Test that PHI is never exposed in logs or error messages
- Test session timeout behavior
- Test role-based access restrictions

## Third-Party Services

- Every third-party service handling PHI must have a signed BAA (Business Associate Agreement)
- Verify HIPAA compliance status before integration
- Never send PHI to analytics services without explicit consent and BAA
- Use HIPAA-compliant email/SMS providers only

## References

- [Medical Web Experts HIPAA Guide](https://www.medicalwebexperts.com/blog/how-to-make-a-hipaa-compliant-healthcare-app/)
- [HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
