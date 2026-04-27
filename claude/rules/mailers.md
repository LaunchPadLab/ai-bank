---
paths:
  - "app/mailers/**/*.rb"
  - "app/views/**/*_mailer/**/*.erb"
  - "test/mailers/**/*.rb"
---

# Mailer Conventions

- Always provide both HTML and text templates.
- Prefer `deliver_later` at explicit call sites; never call `deliver_now` from controllers.
- Create mailer previews in `test/mailers/previews/`.
- Test mailers with Minitest assertions such as `assert_enqueued_email_with`, `assert_emails`, and rendered email assertions.
- Keep mailer logic minimal; formatting belongs in presenters or helpers where appropriate.
- If email delivery is part of broader orchestration, enqueue it from the explicit service or job that owns that workflow.
