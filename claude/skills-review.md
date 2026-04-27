# Review of `claude/skills`

Date: 2026-04-26

## Scope

This review covers every skill package under `claude/skills`, including:

- 43 `SKILL.md` files: 42 skill folders plus the root `claude/skills/SKILL.md`.
- 109 total files in the tree, including references, examples, templates, and helper scripts.
- Metadata, triggering boundaries, instruction quality, safety of examples, internal links, package hygiene, and consistency with the rest of the skill set.

## Executive Summary

The skill library is broad and useful. The strongest areas are Rails TDD workflows, Hotwire/Turbo guidance, policy and domain modeling patterns, and the feature specification/planning/review pipeline. Many skills give agents concrete file paths, commands, and examples, which makes them much more actionable than generic pattern notes.

The highest-risk issues are structural and correctness-related:

- `claude/skills/SKILL.md` duplicates `action-cable-patterns/SKILL.md`, including the same `name: action-cable-patterns` metadata.
- Several examples can guide agents into incorrect Rails code, including a Sidekiq test that mixes Active Job assertions with native Sidekiq jobs, an `enum :type` example that collides with Active Record STI, and a misleading Action Cable "debounce" implementation.
- Some project rules conflict across skills, especially around multi-tenant `account_id` foreign keys.
- Internal references and tooling are partially stale: `rails-model-generator` links to a missing template, `skill-creator` references a missing license and validates a frontmatter schema that does not match this repo.
- Trigger descriptions overlap in ways that can cause the wrong skill or too many skills to load for performance, real-time, architecture, review, auth, and TDD requests.

## Strengths

- The TDD-oriented Rails skills are generally actionable. `rails-model-generator`, `rails-controller`, `rails-service-object`, `form-object-patterns`, `viewcomponent-patterns`, `rails-presenter`, `rails-query-object`, and `rails-concern` give agents RED/GREEN/REFACTOR style workflows with commands and expected failure modes.
- The feature workflow skills (`feature-spec`, `feature-plan`, `feature-review`) have clear responsibilities and useful no-code/no-edit boundaries.
- `turbo-patterns`, `stimulus-patterns`, `performance-optimization`, `policy-patterns`, and `avo-resources` contain a lot of practical pattern knowledge.
- Most linked reference files under `reference/` or `references/` exist and are organized by domain.
- The skill set encodes valuable local conventions, especially Rails 8, Hotwire, Pundit, Minitest, fixtures, UUIDs, explicit account scoping, and "state as records" modeling.

## Priority Findings

### P0: Duplicate root `SKILL.md`

Files:

- `claude/skills/SKILL.md`
- `claude/skills/action-cable-patterns/SKILL.md`

The root `SKILL.md` is a duplicate of the Action Cable skill and uses the same frontmatter name:

```yaml
name: action-cable-patterns
description: Implements real-time features with Action Cable and WebSockets...
```

This creates duplicate skill identity and makes the root of `claude/skills` look like a skill package instead of a container. Any loader that indexes top-level `SKILL.md` files may register two Action Cable skills or treat the root directory as the canonical Action Cable package.

Recommendation:

- Remove `claude/skills/SKILL.md`, or replace it with a true index document that is not a skill package.
- Keep the canonical Action Cable instructions only in `claude/skills/action-cable-patterns/SKILL.md`.

### P0: Authentication cookie conventions conflict

Files:

- `claude/skills/authentication-flow/SKILL.md`
- `claude/skills/hotwire-native-auth/SKILL.md`
- `claude/skills/action-cable-patterns/SKILL.md`

`authentication-flow` uses `cookies.signed[:session_token]` and stores `session.token`. `hotwire-native-auth` uses `cookies.signed.permanent[:session_id]` and stores `session.id`. `action-cable-patterns` follows the `session_token` convention.

That split is dangerous because authentication, Action Cable, and Hotwire Native auth often appear in the same implementation. Agents could create a Rails web session that native auth cannot resume, or a cable connection that rejects otherwise signed-in users.

Recommendation:

- Choose one repo-level session cookie convention.
- Update all auth-adjacent skills to use the same cookie name, value shape, and lookup method.
- Add a short invariant in each related skill: the cookie must match `resume_session`, `start_new_session_for`, and Action Cable `find_verified_user`.

### P0: Multi-tenant foreign key guidance contradicts migration guidance

Files:

- `claude/skills/multi-tenant-patterns/SKILL.md`
- `claude/skills/database-migrations/SKILL.md`
- `claude/skills/refactoring-patterns/SKILL.md`
- `claude/skills/rails-model-generator/SKILL.md`

`multi-tenant-patterns` states that tenant-scoped tables should include `account_id` but avoid foreign key constraints. `database-migrations` presents `add_reference :events, :account, null: false, foreign_key: true, index: true` as the safe pattern. `rails-model-generator` also shows `organization:references` and `foreign_key: true` in generated migrations.

The multi-tenant guidance may be an intentional architecture decision, but it is not reconciled with the general migration skills. Agents using both skills can produce inconsistent schemas.

Recommendation:

- Add a callout to `database-migrations`: when the project has chosen soft account references, use `foreign_key: false` for `account_id` and preserve indexes.
- Add rationale and exceptions to `multi-tenant-patterns`: explain why account foreign keys are omitted, when other foreign keys should remain, and when a hard FK is still appropriate.
- Update model/migration generator examples so tenant-scoped references do not silently violate the multi-tenant rule.

### P0: Sidekiq test example mixes Active Job and native Sidekiq APIs

File:

- `claude/skills/sidekiq-setup/SKILL.md`

The native Sidekiq job example uses `include Sidekiq::Job` and enqueues with `perform_async`, but the test includes `ActiveJob::TestHelper` and wraps `perform_async` in `assert_enqueued_email_with`.

That assertion is for Active Job mail delivery, not native Sidekiq job queues. Agents copying this example will likely write tests that either fail or test the wrong queueing layer.

Recommendation:

- Split the testing section into two paths:
  - Active Job: `ApplicationJob`, `perform_later`, `assert_enqueued_jobs`, `assert_enqueued_email_with`.
  - Native Sidekiq: `include Sidekiq::Job`, `perform_async`, `Sidekiq::Testing.fake!`, and assertions on `SendWelcomeEmailJob.jobs.size`.
- State which path is preferred for this repo and why.

### P0: `events-patterns` uses `enum :type`

File:

- `claude/skills/events-patterns/SKILL.md`

The `TrackingEvent` example uses:

```ruby
enum :type, { page_view: 0, link_click: 1, form_submit: 2 }
```

In Active Record, `type` is reserved for single-table inheritance. This example can cause subtle production bugs if copied into a model.

Recommendation:

- Rename the column and enum to `event_kind`, `tracking_kind`, or another non-reserved name.
- Avoid showing `self.inheritance_column = :_disabled` unless the skill is explicitly teaching legacy remediation.

### P1: Action Cable "debouncing" is really first-event rate limiting

Files:

- `claude/skills/action-cable-patterns/SKILL.md`
- `claude/skills/SKILL.md` if the duplicate is retained

The `BroadcastService.debounced_broadcast` example uses `Rails.cache.fetch("broadcast:#{key}", expires_in: wait) { yield; true }`. This prevents repeated execution during the cache window, but it does not debounce in the usual sense of coalescing rapid events and running once after the quiet period.

Recommendation:

- Rename the example to rate limiting, or replace it with a true delayed/coalescing pattern using Sidekiq, Solid Queue, or Redis `SET NX EX`.
- Include the desired semantics: first event wins, last event wins, or aggregate-and-flush.

### P1: Broken or stale internal references

Files:

- `claude/skills/rails-model-generator/SKILL.md`
- `claude/skills/rails-architecture/SKILL.md`
- `claude/skills/feature-plan/references/FEATURE_TEMPLATE.md`
- `claude/skills/feature-review/references/FEATURE_TEMPLATE.md`

Issues:

- `rails-model-generator` links to `templates/model_test.erb`, but no `templates/` directory exists in that skill package.
- `rails-architecture` references non-existent or mismatched skill names: `authorization-pundit`, `hotwire-patterns`, and `api-versioning`. The local equivalents appear to be `policy-patterns`, `turbo-patterns`, and `api-patterns`.
- The feature plan/review template files contain only the text `../../feature-spec/references/FEATURE_TEMPLATE.md`, not a markdown link, copy, or symlink.

Recommendation:

- Add the missing model test template or replace the links with existing reference paths.
- Update architecture references to actual skill slugs.
- Turn feature template stubs into real markdown links, symlinks, or short wrapper documents.

### P1: `skill-creator` tooling does not match the local skill corpus

Files:

- `claude/skills/skill-creator/SKILL.md`
- `claude/skills/skill-creator/scripts/quick_validate.py`
- `claude/skills/skill-creator/scripts/package_skill.py`
- `claude/skills/skill-creator/scripts/init_skill.py`

Issues:

- Frontmatter says `license: Complete terms in LICENSE.txt`, but no `LICENSE.txt` exists in the package.
- `skill-creator/SKILL.md` says only `name` and `description` should appear in frontmatter, but local skills use `allowed-tools`, `user-invocable`, `argument-hint`, `disable-model-invocation`, `context`, and `agent`.
- `quick_validate.py` only allows a subset of fields and would reject many skills in this repo.
- `package_skill.py` usage text references `utils/package_skill.py`, but the script lives in `scripts/`.
- Scripts rely on `PyYAML`, but there is no dependency note, `requirements.txt`, or `pyproject.toml`.

Recommendation:

- Decide whether `skill-creator` documents a generic upstream skill format or this repo's extended format.
- If it is local guidance, update the schema and validator to match actual frontmatter conventions.
- Add a minimal dependency note and smoke test command for the scripts.
- Add or remove the missing license reference.

### P1: Generated Python bytecode is present

File:

- `claude/skills/skill-creator/scripts/__pycache__/quick_validate.cpython-314.pyc`

Generated bytecode should not be committed or packaged into skill archives.

Recommendation:

- Remove the `__pycache__/` artifact.
- Add `__pycache__/` and `*.pyc` to the appropriate ignore file.
- Update packaging to exclude cache files defensively.

### P1: `testing-patterns` is named like testing but contains refactoring content

Files:

- `claude/skills/testing-patterns/SKILL.md`
- `claude/skills/refactoring-patterns/SKILL.md`

`testing-patterns` has `name: testing-patterns`, but its description and body are "Eight proven refactoring patterns" and `# Refactoring Patterns`. This overlaps heavily with `refactoring-patterns` and leaves no dedicated general Rails testing skill.

Recommendation:

- Either rename `testing-patterns` to something like `tdd-refactor-patterns`, or rewrite it into a true testing skill covering Minitest, fixtures, integration/system tests, jobs/mailers, time helpers, stubbing, and browser verification.
- Keep `refactoring-patterns` as the strategic cleanup/orchestration skill.

### P1: Claude-specific shell interpolation appears in skill bodies

Files:

- `claude/skills/code-review/SKILL.md`
- `claude/skills/avo-resources/SKILL.md`

Some skills use Claude Code-style inline shell syntax such as `!` commands. In Cursor or other runtimes, those snippets may be echoed literally instead of executed.

Recommendation:

- Replace magic shell interpolation with plain instructions: "Run `git diff ...`" or "List `app/avo/resources/`".
- If Claude Code-specific syntax is intentional, label it as runtime-specific.

### P1: Agent orchestration instructions are not portable

Files:

- `claude/skills/implement-patterns/SKILL.md`
- `claude/skills/refactoring-patterns/SKILL.md`

These skills rely on named `@...-agent` handoffs. That can be useful in a Claude Code setup, but it is brittle in Cursor or any environment where agent names differ.

Recommendation:

- Add a fallback path: if named subagents are unavailable, execute the phases sequentially and load the corresponding skills.
- Map agent names to local skill names and file targets.
- Include verification commands for each phase.

## Trigger and Metadata Findings

### Duplicate and conflicting activation boundaries

The skill descriptions are strong individually, but several clusters share the same trigger language:

- Real-time: `action-cable-patterns` and `turbo-patterns` both mention live updates, broadcasting, and real-time UI.
- Performance: `caching-strategies` and `performance-optimization` both mention performance and optimization.
- Architecture/review: `rails-architecture`, `code-review`, `feature-review`, `implement-patterns`, and `refactoring-patterns` all use architecture, review, or pattern language.
- TDD/testing: `tdd-cycle`, `red-test-patterns`, `testing-patterns`, and the Rails generator skills all mention TDD and refactoring phases.
- Auth/security: `authentication-flow`, `hotwire-native-auth`, and `policy-patterns` can overlap when a user says "secure controllers" or "auth".

Recommendations:

- Make the first sentence of each description more exclusive.
- Use concrete trigger phrases: "Action Cable channels/subscriptions" for `action-cable-patterns`, "Turbo Frames/Streams/morphing" for `turbo-patterns`, "cache keys/fragments/Russian doll" for `caching-strategies`, and "N+1/query plans/memory/Bullet" for `performance-optimization`.
- Add "prefer X when..." guidance where two skills intentionally overlap.

### Frontmatter conventions are inconsistent

Observed patterns:

- Generator/action skills often use `allowed-tools`.
- Reference skills often use `user-invocable: false`.
- Forked review/planning skills use `context` and `agent`.
- `feature-plan`, `feature-spec`, `feature-review`, and `tdd-cycle` use `disable-model-invocation`.
- `hotwire-native-path-config` has only `name` and `description`.
- Some skills combine `user-invocable: false` with user-facing argument hints or "Use proactively" descriptions.

Recommendations:

- Document a frontmatter schema matrix:
  - Generator skill: `allowed-tools`, user-invocable by default.
  - Reference skill: `user-invocable: false`, no imperative "creates/implements" wording.
  - Forked analysis skill: `context`, `agent`, and `disable-model-invocation` where appropriate.
  - Runtime-specific skill: note which environment supports fields like `agent`.
- Validate all skills against that matrix.

### `allowed-tools` includes potentially nonstandard values

Files:

- `claude/skills/rails-controller/SKILL.md`
- `claude/skills/rails-concern/SKILL.md`
- `claude/skills/rails-presenter/SKILL.md`
- `claude/skills/rails-query-object/SKILL.md`

These include `Bash(bin/rails test:*)`. If this syntax is supported by the runner, it is fine. If not, it may silently fail or be ignored.

Recommendation:

- Confirm the allowed-tools syntax for the target runtime.
- If unsupported, replace with `Bash` or the documented permission syntax.

## Content Quality Findings

### Missing standard verification sections

Several reference-heavy skills provide good patterns but do not consistently end with agent verification steps.

Examples:

- `api-patterns`
- `events-patterns`
- `policy-patterns`
- `stimulus-patterns`
- `tailwind-patterns`
- `turbo-patterns`
- `lint-patterns`

Recommendation:

- Add a short "Agent Verification" section to each skill:
  - Minimal test command.
  - Lint command if relevant.
  - Browser smoke test for Turbo/Stimulus/UI skills.
  - Manual verification checklist for skills that produce docs or specs.

### TDD guidance conflicts around validation messages

File:

- `claude/skills/tdd-cycle/SKILL.md`

The TDD skill warns against brittle exact validation message assertions, but several model/form examples assert English strings such as `"can't be blank"`.

Recommendation:

- Prefer `errors.added?(:field, :blank)` for model tests.
- Allow exact strings only when testing user-facing copy or when locale is intentionally fixed.
- Update examples across model/form skills to match the policy.

### Rails 8 stack assumptions need scoping

Some skills assume specific stack choices:

- `stimulus-patterns` leans toward importmap.
- `sidekiq-setup` teaches Sidekiq even though Rails 8 greenfield apps may default to Solid Queue.
- `rails-architecture` assumes Redis-backed caching and Sidekiq in some examples.
- `hotwire-native-path-config` includes product-specific paths such as `LifeMuse-iOS`.

Recommendation:

- Add a short "Assumptions" block near the top of stack-sensitive skills.
- Include alternatives or stop conditions: "If this repo uses Solid Queue, do not apply Sidekiq setup without confirmation."
- Parameterize product-specific examples.

### Controller test location is ambiguous

File:

- `claude/skills/rails-controller/SKILL.md`

The quick start points to `test/controllers/`, while examples use `ActionDispatch::IntegrationTest`, which many Rails projects place under `test/integration/`.

Recommendation:

- State the repo convention explicitly.
- Use one test directory consistently, or explain why controller-style integration tests live in `test/controllers/`.

### Active Storage delete link example may be stale for Turbo

File:

- `claude/skills/active-storage-setup/SKILL.md`

Some Rails/Turbo apps need `data: { turbo_method: :delete }` instead of `method: :delete`.

Recommendation:

- Update delete link examples to modern Turbo-compatible syntax.
- Mention the distinction if supporting non-Turbo Rails UJS apps.

## Package Structure and Hygiene

### `reference/` vs `references/`

Most Rails pattern skills use `reference/`; feature and skill-creator packages use `references/`.

Recommendation:

- Either standardize on one spelling or document the convention.
- If standardizing, prefer a gradual migration to avoid breaking existing links.

### Long skills exceed local guidance

`skill-creator` recommends keeping skill bodies concise and moving detail into reference files. Several skills exceed that style:

- `action-cable-patterns`
- `refactoring-patterns`
- `state-records-patterns`
- `tailwind-patterns`
- `turbo-patterns`

Recommendation:

- Split large pattern catalogs into reference files where the first 100-150 lines can tell the agent when to load which reference.
- Keep quick-start workflows in `SKILL.md`; move examples, recipes, and deep reference material into `reference/`.

## Per-Skill Notes

| Skill | Assessment | Recommendation |
| --- | --- | --- |
| `SKILL.md` at root | Duplicate of `action-cable-patterns`; wrong root-level package. | Remove or replace with non-skill index. |
| `action-cable-patterns` | Strong channel examples, but auth cookie must align and debounce example is misleading. | Align cookie convention; replace debounce snippet. |
| `action-mailer-patterns` | Useful mailer workflow and previews. | Add standard verification checklist for mailer previews, delivery tests, and jobs if async. |
| `active-storage-setup` | Practical upload setup. | Update Turbo delete examples and add direct-upload/browser smoke verification. |
| `api-patterns` | Solid REST/Jbuilder reference. | Add versioning boundary and verification commands for request tests. |
| `authentication-flow` | Useful Rails 8 auth overview. | Align session cookie convention with native auth and Action Cable. |
| `avo-resources` | Detailed and locally useful. | Resolve `user-invocable: false` vs "Use proactively"; remove Claude-specific shell interpolation. |
| `caching-strategies` | Good cache pattern coverage. | Narrow trigger wording to caching-specific terms to avoid performance skill collisions. |
| `code-review` | Clear review stance and static-analysis checklist. | Consider `disable-model-invocation: true`; replace `!` shell snippets with portable instructions. |
| `database-migrations` | Strong safety checklist. | Reconcile foreign key guidance with multi-tenant account references; document `strong_migrations` dependency for `safety_assured`. |
| `events-patterns` | Good event/activity modeling. | Replace `enum :type` with a non-STI column name. |
| `feature-plan` | Clear planning workflow. | Make feature template reference a real link and verify output path exists. |
| `feature-review` | Useful review boundary for specs. | Make feature template reference a real link; clarify how it differs from `code-review` in trigger wording. |
| `feature-spec` | Strong specification workflow. | Add repo-layout check before writing to `docs/features/[feature-name].md`. |
| `form-object-patterns` | Actionable form object TDD guidance. | Replace exact validation string assertions where practical. |
| `hotwire-native-android` | Good Android-specific native bridge guidance. | Add assumptions/version notes for Hotwire Native APIs. |
| `hotwire-native-auth` | Valuable native auth bridge workflow. | Align cookie convention with Rails auth; call out that generated auth may differ. |
| `hotwire-native-ios` | Good iOS-specific native bridge guidance. | List `AUTH.md` and `NAVIGATION.md` like Android does. |
| `hotwire-native-path-config` | Useful focused path config reference. | Add frontmatter controls and parameterize product-specific paths. |
| `i18n-patterns` | Useful localization guidance. | Add verification for missing translations and locale-specific tests. |
| `implement-patterns` | Helpful feature orchestration. | Add non-subagent fallback and reconcile service-object opinions with `rails-service-object`. |
| `lint-patterns` | Practical lint reference. | Add explicit safe/unsafe autocorrect guidance and verification commands. |
| `multi-tenant-patterns` | Encodes important account-scoping conventions. | Reconcile no-FK rule with migration/model skills and add rationale/exceptions. |
| `performance-optimization` | Strong N+1/query/performance content. | Keep trigger wording focused on profiling, queries, memory, and Bullet. |
| `policy-patterns` | Strong Pundit coverage. | Align `user-invocable: false` with imperative "Implements" description. |
| `rails-architecture` | Valuable decision tree. | Fix references to actual skill names and add a fallback when multiple patterns apply. |
| `rails-concern` | Useful shared behavior workflow. | Validate `allowed-tools` syntax and add when-not-to-use concern guidance up front. |
| `rails-controller` | Good controller TDD flow. | Normalize test directory/base-class convention; validate `allowed-tools` syntax. |
| `rails-model-generator` | Strong TDD model creation workflow. | Add missing template or remove broken link; reconcile FK examples with multi-tenancy. |
| `rails-presenter` | Good display-logic extraction workflow. | Validate `allowed-tools` syntax and add view/helper boundary examples. |
| `rails-query-object` | Useful query encapsulation guidance. | Validate `allowed-tools` syntax and add query-plan/performance verification for complex queries. |
| `rails-service-object` | Strong service object pattern. | Reconcile with `implement-patterns` guidance that discourages service objects in some cases. |
| `red-test-patterns` | Useful RED-phase templates. | Link clearly to `tdd-cycle` and specify when this skill should load instead of full TDD workflow. |
| `refactoring-patterns` | Useful modernization/orchestration guidance. | Add non-subagent fallback and avoid duplicate scope with `testing-patterns`. |
| `sidekiq-setup` | Useful Sidekiq setup coverage. | Fix native Sidekiq test examples; add Solid Queue decision note. |
| `skill-creator` | Valuable general skill-writing guidance. | Update frontmatter schema, missing license, validator, package paths, and dependency notes. |
| `state-records-patterns` | Strong domain modeling guidance. | Consider moving long examples into references and add migration/test verification checklist. |
| `stimulus-patterns` | Strong Stimulus reference. | Add bundler/importmap assumptions and browser verification steps. |
| `tailwind-patterns` | Useful styling patterns. | Add visual/browser verification and consider splitting long reference content. |
| `tdd-cycle` | Good process skill. | Harmonize validation assertion guidance with model/form examples. |
| `testing-patterns` | Misnamed; content is refactoring, not testing. | Rename or rewrite as a true Rails testing skill. |
| `turbo-patterns` | Strong Hotwire content. | Narrow real-time trigger overlap with Action Cable and add browser/system verification checklist. |
| `viewcomponent-patterns` | Good reusable component TDD workflow. | Add preview/browser verification and note component test conventions. |

## Recommended Cleanup Plan

1. Remove or replace the duplicate root `claude/skills/SKILL.md`.
2. Fix correctness bugs in examples: auth cookie convention, Sidekiq tests, `enum :type`, and Action Cable debounce semantics.
3. Repair broken links and missing files: model test template, architecture skill names, feature template stubs, and skill-creator license.
4. Remove generated bytecode and harden packaging exclusions.
5. Define and document frontmatter conventions, then update `quick_validate.py` to enforce them.
6. Normalize trigger descriptions for overlapping skills.
7. Add a short verification section to every skill that can lead to code edits.
8. Decide whether `testing-patterns` should be renamed or rewritten.
9. Split the longest skills into quick-start `SKILL.md` files plus deeper references.

## Suggested Validation Checks

After cleanup, add one repeatable validation command or script that checks:

- Every skill folder has exactly one `SKILL.md`.
- No root-level `claude/skills/SKILL.md` is treated as a skill unless intentionally documented.
- Frontmatter matches the local schema.
- Internal markdown links resolve.
- No `__pycache__`, `*.pyc`, or generated artifacts are included.
- Skill names are unique.
- Referenced local skill slugs exist.

This would prevent the current class of drift from recurring as new skills are added.
