# Codex Instructions: Root Project Scope

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/cli.md`
- `claude/rules/frontend.md`
- `claude/rules/git-conventions.md`
- `claude/rules/principles.md`

## Source: `claude/rules/cli.md`

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


## Source: `claude/rules/frontend.md`

# Frontend Conventions

- Prefer Hotwire (Turbo + Stimulus) over SPA frameworks.
- Keep JavaScript thin and focused on progressive enhancement.
- Put Stimulus controllers in `app/javascript/controllers/`.
- Use Turbo Frames and Turbo Streams for server-rendered UI updates.
- Ask before adding npm packages or introducing a new frontend build stack.
- For native shell decisions, defer to the Hotwire Native iOS/Android skills and app-specific files.


## Source: `claude/rules/git-conventions.md`

# Commits
- Conventional commits: feat: fix: chore:
- Imperative mood: "Fix bug" not "Fixed bug"

# Default Branch
- Default branch is dev

# Always branch first
- Never work on dev, staging, or main branches. 
- Remind me if I haven't branched.


## Source: `claude/rules/principles.md`

# Development Principles

- **Rails doctrine first:** Optimize for programmer happiness through convention over configuration, conceptual compression, and integrated Rails defaults.
- **The menu is omakase:** Prefer the framework's curated stack and local project choices before adding new gems, front-end frameworks, service layers, or infrastructure.
- **KISS:** Prefer standard CRUD controllers, conventional routing, and Rails defaults. Add abstractions only when the current code needs them.
- **DRY is about knowledge, not shape:** Keep one authoritative representation of a business rule, but tolerate small duplication before extracting the wrong abstraction.
- **YAGNI:** Implement only what is required now. Avoid speculative flags, settings, base classes, and extension points.
- **Integrated systems:** Keep related behavior inside the Rails app unless there is a concrete operational need to split it out.
- **Explicit over implicit:** Prefer named methods, explicit calls, and clear ownership over hidden callbacks or surprising metaprogramming.
- **Composition over inheritance:** Favor concerns, delegation, and small collaborators over deep class hierarchies.
- **Decision ladder:** Use model methods for cohesive aggregate behavior; concerns for shared horizontal behavior; query objects for reusable read complexity; form objects for complex input boundaries; services for orchestration, transactions, side effects, or external systems.
- **Callbacks:** Use callbacks only for local data normalization and defaults. Side effects such as emails, API calls, job enqueueing, and related-record orchestration belong at explicit call sites or in services.
- **No premature abstraction:** Extract only after a pattern is real, repeated, and clearer when named.
