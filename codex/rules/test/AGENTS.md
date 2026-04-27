# Codex Instructions: test

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/anti-patterns.md`
- `claude/rules/testing.md`

## Source: `claude/rules/anti-patterns.md`

# Anti-Patterns to Avoid

- **God object:** A class with unrelated reasons to change. Extract by responsibility: query objects for reads, concerns for shared horizontal behavior, services for orchestration, and presenters/components for display.
- **Service graveyard:** Do not create services for trivial CRUD or model-local behavior. `user.update!(name: params[:name])` is fine inline when it is the whole operation.
- **Anemic model:** Do not strip cohesive domain behavior from the model that owns the state just to keep models artificially thin.
- **Callback spaghetti:** Do not chain `after_create` or `after_save` callbacks for emails, jobs, APIs, or creating related records. Use explicit call sites or services for contextual side effects.
- **STI abuse:** Avoid STI when many columns are subtype-specific. Prefer separate tables or polymorphic associations when shapes diverge.
- **N+1 ignorance:** Eager-load associations you know will be accessed. Use `strict_loading` to catch accidental lazy loads in development.
- **Kitchen sink concern:** Concerns must be narrow and focused. If a concern has multiple responsibilities, split it or move orchestration elsewhere.


## Source: `claude/rules/testing.md`

# Minitest Principles & Conventions

1. **Always use Minitest, never RSpec.** This project uses Minitest with ActiveSupport::TestCase for models, ActionDispatch::IntegrationTest for controllers/requests, and ActionView::TestCase for helpers. Do not generate RSpec syntax (`describe`, `it`, `expect`) under any circumstances.

2. **Follow Rails test directory conventions.** Place tests in `test/models/`, `test/controllers/`, `test/integration/`, `test/system/`, `test/services/`, `test/mailers/`, etc. Mirror `app/` structure. Test files end in `_test.rb`. Test classes inherit from the appropriate Rails test case base class.

3. **Use `test "descriptive name"` block syntax over `def test_` method syntax.** Write human-readable test names: `test "user cannot book past dates"` not `def test_user_cannot_book_past_dates`. Keep names behavior-focused, not implementation-focused.

4. **Use standard Minitest assertions.** Prefer `assert`, `assert_equal expected, actual`, `assert_nil`, `assert_raises`, `assert_difference`, `assert_no_difference`, `assert_enqueued_email_with`, `assert_response`, `assert_redirected_to`. Never use `should` or `expect` matchers. Argument order is always `expected, actual` — never reversed.

5. **Use fixtures for test data.** Rails 8 uses fixtures by default. Define test data in `test/fixtures/*.yml` and reference via `users(:alice)`. Do not introduce an alternate test-data library unless explicitly told to. Keep fixtures minimal — only attributes required for validity.

6. **One assertion per logical concept.** Each test should verify one behavior. Multiple assertions are fine when they verify facets of the same outcome (e.g., checking a redirect and a flash message together). Do not test unrelated behaviors in a single test block.

7. **Use `setup` for shared context, not inheritance tricks.** Use `setup do ... end` blocks for common test state. Avoid deep test class hierarchies or shared example modules. Tests should be readable top-to-bottom without chasing mixins.

8. **Run tests with `bin/rails test` commands.** Use `bin/rails test test/models/user_test.rb` for a file, `bin/rails test test/models/user_test.rb:42` for a specific line, `bin/rails test:models` for a directory. For system tests use `bin/rails test:system`. Always provide the run command when writing tests.

9. **Use Minitest APIs for jobs and mailers.** For Action Mailer, use `assert_enqueued_email_with` and `assert_emails`. For native Sidekiq jobs, use Sidekiq testing helpers (`Sidekiq::Testing.fake!`, `.jobs.size`, `.drain`, or inline mode). Do not use RSpec-style enqueue matchers.
