---
alwaysApply: true
---

# CLI Commands

## Routine Commands

```bash
bin/dev
bin/rails server
bin/rails test
bin/rails test test/models/user_test.rb
bin/rails test test/models/user_test.rb:42
bin/rails test:system
bin/rails db:migrate
bin/rails db:migrate:status
bin/rails routes
bin/rails routes -g user
bin/rails console
bin/rails runner "puts User.count"
bin/brakeman --no-pager
bundle exec bundler-audit check --update
bundle install
bundle update <gem>
```

## Linting

```bash
bin/rubocop -a
bin/rubocop app/models/
bin/rubocop --only Style/StringLiterals
```

Prefer `bin/rubocop -a` for safe autocorrect. Ask before running `bin/rubocop -A` because it applies unsafe corrections.

## Generators

```bash
bin/rails g model User name:string email:string
bin/rails g migration AddRoleToUsers role:integer
bin/rails g controller Users index show
```

Rails model generators create models and migrations. Add fixtures manually in `test/fixtures/` when tests need data.

## Ask First or Local-Only Commands

- `kill -9 $(lsof -t -i :3000)` - ask first; prefer graceful shutdown before force-killing.
- `rm tmp/pids/server.pid` - use only for a confirmed stale local Rails PID.
- `bin/rubocop -A` - ask first; unsafe autocorrect can change behavior.
- `bin/rails db:rollback` - confirm scope and migration state first.
- `bin/rails db:reset` - destructive; local-only and ask first.
- `bin/rails db:schema:load` - destructive to the target database; ask first.
- `bin/rails destroy ...` - destructive generator rollback; ask first.

## Native Sidekiq

```bash
bundle exec sidekiq
bundle exec sidekiq -C config/sidekiq.yml
```

Use native Sidekiq commands when the app uses Sidekiq jobs. Do not use another queue backend's commands unless the repo has explicitly chosen that backend.

## Assets and JavaScript Dependencies

```bash
bin/importmap pin <package>
bin/importmap unpin <package>
```

Ask before adding new JavaScript packages.
