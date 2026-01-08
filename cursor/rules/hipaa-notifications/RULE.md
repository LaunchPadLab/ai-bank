---
description: HIPAA-compliant notification and messaging rules
globs:
  - "code/**/app/jobs/**/*.rb"
  - "code/**/app/mailers/**/*.rb"
  - "code/**/app/services/**/*notification*.rb"
  - "code/**/app/services/**/*message*.rb"
alwaysApply: false
---

# HIPAA-Compliant Notifications & Messaging

## The Golden Rule

**NEVER include any of the 18 PHI identifiers in any notification that could be seen by someone other than the intended recipient.**

Consider: notifications appear on lock screens, emails can be forwarded, SMS can be seen by others.

## Prohibited Content in Notifications

Never include:
- Patient names (other than the recipient's own name in authenticated contexts)
- Provider names with specialty (reveals nature of care)
- Appointment types or specialties
- Diagnosis, condition, or treatment information
- Lab test names or results
- Medication names
- Facility names that reveal treatment type (e.g., "Cancer Center")

### BAD Examples ❌
```ruby
"Your appointment with Dr. Smith (Oncology) is tomorrow at 3pm"
"Lab results for your diabetes A1C test are ready"
"Prescription for Metformin is ready for pickup"
```

### GOOD Examples ✅
```ruby
"You have an upcoming appointment. Log in to view details."
"New information is available in your portal."
"A message is waiting for you."
```

## Key Implementation Principles

1. **Generic subjects and bodies** — Email subjects must never reveal health context
2. **Whitelist approach** — Use predefined safe message templates, never dynamic PHI
3. **Details behind auth** — All specifics viewable only after secure portal login
4. **In-app messaging can contain PHI** — Authenticated portal context is secure; notifications about those messages must remain generic
