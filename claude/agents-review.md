# Review of `claude/agents`

Date: 2026-04-26

## Scope

This review covers all 42 Markdown agent files under `claude/agents`, plus the related agent documentation in `README.md` and the current skill slugs under `claude/skills`.

Review focus:

- Frontmatter shape and consistency.
- Permission and tool-boundary alignment.
- Agent prompt quality and actionability.
- Skill linkage after the recent skills cleanup.
- References to nonexistent agents, helpers, or workflows.
- Fit with the Rails 8, Hotwire, Minitest, Pundit, and multi-tenant conventions used elsewhere in this repository.

Context7 was not needed for this pass because the key issues are local consistency and runner-specific frontmatter conventions already present in this repo. If you want to validate exact support for fields such as `permissionMode`, `background`, `memory`, and `disallowedTools`, check the active Claude/Cursor runner docs before enforcing them automatically.

## Executive Summary

The agent catalog is useful and broad. Most Rails specialists are clear, skill-linked, and aligned with project conventions. All `skills:` entries declared in agent frontmatter currently resolve to existing skill folders, which is a strong baseline after the skills cleanup.

The main risks are:

- Several read-only or plan-mode agents still use implementation language in their prompts.
- Some generic imported agents reference a nonexistent `context-manager`, fake collaborator agents, or unavailable orchestration primitives.
- `auth-agent` and the preloaded `authentication-flow` skill describe different authentication products.
- `frontend-developer` is React/Vue/Angular-centric, while this repo's UI guidance is Rails, Hotwire, Stimulus, Tailwind, and ViewComponent.
- Hotwire Native iOS/Android agents duplicate long-form content but do not preload the corresponding skills.
- `README.md` documents only `name`, `description`, `model`, and optional `color`, but real agents use many additional fields.

## What Looks Good

- Every frontmatter `skills:` slug points to an existing skill under `claude/skills`.
- Many specialist agents are thin wrappers around canonical skills, which reduces drift: `policy-agent`, `lint-agent`, `stimulus-agent`, `turbo-agent`, `tailwind-agent`, `query-agent`, `presenter-agent`, `mailer-agent`, `jobs-agent`, and others.
- The feature workflow agents have clear boundaries: `feature-spec-agent`, `feature-plan-agent`, and `feature-review-agent`.
- The code review, security, and compliance agents use read-only metadata (`disallowedTools: Write, Edit`, `permissionMode: plan`) where review behavior is intended.
- Most Rails-specific agents repeat useful local conventions: Minitest, fixtures, UUIDs, account scoping, Pundit, and Hotwire.

## Priority Findings

### P0: `compliance-auditor` contradicts its read-only metadata

File: `claude/agents/compliance-auditor.md`

Frontmatter sets:

```yaml
disallowedTools: Write, Edit
permissionMode: plan
```

But the body instructs the agent to "Implement solutions ensuring regulatory compliance" and includes an "Implementation Phase" with technical control deployment, monitoring setup, and automation. It also includes checklist items like "100% control coverage verified" and canned compliance score examples that can read like guaranteed metrics rather than evidence-based findings.

Recommendation:

- Make the default mode explicitly audit-only: assess, map controls, request evidence, identify gaps, and recommend remediation.
- Move implementation language into a separate "Remediation mode" that requires write-capable configuration and explicit user approval.
- Replace guaranteed metrics with sourced evidence requirements. Do not allow fabricated compliance scores.

### P0: `auth-agent` conflicts with `authentication-flow`

File: `claude/agents/auth-agent.md`

The agent says it implements custom passwordless authentication with `Identity`, `Session`, and `MagicLink` models and "without Devise." Its frontmatter preloads `authentication-flow`, but that skill documents Rails 8 generator-style authentication with `User`, `Session`, `has_secure_password`, password reset flows, and token-backed sessions.

These are different architectures. An agent following both will produce confused authentication behavior.

Recommendation:

- Choose one source of truth.
- If passwordless magic links are the desired product, create or restore a dedicated `passwordless-auth` / `hotwire-native-auth` style skill and preload that instead.
- If Rails generator auth is the desired product, rewrite `auth-agent` to match `authentication-flow`.
- Update `refactoring-patterns` references to `@auth-agent` once the direction is chosen.

### P0: Several agents depend on nonexistent `context-manager`

Files include:

- `claude/agents/frontend-developer.md`
- `claude/agents/ui-designer.md`
- `claude/agents/rails-expert.md`
- `claude/agents/database-optimizer.md`
- `claude/agents/postgres-pro.md`
- `claude/agents/prompt-engineer.md`
- `claude/agents/compliance-auditor.md`
- `claude/agents/performance-monitor.md`

These prompts instruct the agent to query a "context-manager" and sometimes send JSON payloads to it. There is no `context-manager` agent file in `claude/agents`, and this workflow is not actionable in the current catalog.

Recommendation:

- Remove the JSON context-manager ritual from these prompts.
- Replace it with concrete repo exploration steps: read `README.md`, inspect relevant files, use `rg`/glob searches, and ask targeted questions when context is missing.
- If a context manager exists outside this repo, document that dependency in `README.md` and the relevant agent prompts.

### P1: `frontend-developer` is misaligned with this Rails/Hotwire repo

File: `claude/agents/frontend-developer.md`

This agent is centered on React 18+, Vue 3+, Angular 15+, TypeScript interfaces, Storybook, `/src/components/`, and SPA-style metrics. That conflicts with the local UI stack represented by `turbo-agent`, `stimulus-agent`, `tailwind-agent`, `view-component-agent`, and the skills catalog.

Recommendation:

- Retarget the agent to Rails views, Hotwire, Stimulus, Tailwind, ViewComponent, system tests, and progressive enhancement.
- Or mark it explicitly as out-of-scope unless the user is working in a separate SPA package.
- Remove references to nonexistent collaborators such as `qa-expert`, `performance-engineer`, `websocket-engineer`, `deployment-engineer`, and `security-auditor`.

### P1: `implement-agent` requires `runSubagent` with no fallback

File: `claude/agents/implement-agent.md`

The agent says to use `runSubagent` for each specialized task and never implement all layers directly. If the host runtime does not expose a `runSubagent` primitive, the agent has no valid execution path.

Recommendation:

- Replace `runSubagent` with the actual orchestration mechanism used by this environment.
- Add a fallback: if subagents are unavailable, execute the same dependency-ordered workflow directly while loading the relevant skills.
- Keep delegation as preferred, not the only allowed path.

### P1: Hotwire Native agents duplicate skill content but do not preload skills

Files:

- `claude/agents/hotwire-native-ios-agent.md`
- `claude/agents/hotwire-native-android-agent.md`

These agents contain hundreds of lines of setup and bridge guidance, but their frontmatter has no `skills:` key. The repo now has canonical skills for `hotwire-native-ios`, `hotwire-native-android`, `hotwire-native-auth`, and `hotwire-native-path-config`.

Recommendation:

- Add `skills:` to preload the corresponding platform skill.
- Consider trimming the agent bodies to role, boundaries, project assumptions, and "follow the preloaded skill" instructions.
- Add cross-links to auth and path-config skills where those topics are in scope.

### P1: `rails-expert` has version drift and generic enterprise residue

File: `claude/agents/rails-expert.md`

The description says Rails 8.x, but the checklist and feature section say Rails 7.x. The body also references `context-manager`, nonexistent collaborator agents, 95% coverage as a blanket target, GraphQL/Kubernetes defaults, and other broad enterprise concerns that are not consistently part of this repo's conventions.

Recommendation:

- Update Rails 7 references to Rails 8.
- Preload `rails-architecture` or explicitly defer to specialist skills.
- Remove nonexistent collaborator names or replace them with local agents.
- Soften global coverage/deployment claims into project-dependent guidance.

### P1: Model, concern, and service guidance needs a shared decision order

Files:

- `claude/agents/model-agent.md`
- `claude/agents/concerns-agent.md`
- `claude/agents/service-agent.md`

`model-agent` says to put domain logic in models, not service objects. `concerns-agent` says concerns are the primary abstraction for shared behavior, not service objects. `service-agent` says services are appropriate for cross-model transactions and side effects.

These can all be reasonable, but without a decision order they read as competing rules.

Recommendation:

- Add the same decision ladder to all three agents:
  - Model methods for cohesive domain behavior on one aggregate.
  - Concerns for shared horizontal behavior across models/controllers.
  - Query objects for reusable read/query complexity.
  - Form objects for complex form input.
  - Services for orchestration across models, transactions, side effects, or external systems.
- Replace absolute "not service objects" wording with scoped preference language.

### P1: README agent guidance is stale

File: `README.md`

The "Adding a New Agent" section says to use `name`, `description`, `model`, and optionally `color`. Actual agents also use `skills`, `maxTurns`, `disallowedTools`, `permissionMode`, `isolation`, `background`, and `memory`. No current agent uses `color`.

Recommendation:

- Update README with the actual frontmatter schema and when each field should be used.
- Document standard `skills:` formatting and indentation.
- Either remove `color` from the template or start using it consistently.

## Secondary Findings

### Read-only wording in `security-agent`

File: `claude/agents/security-agent.md`

The description says the agent "applies OWASP best practices" while frontmatter disallows writing. The body is mostly audit-focused, so this is mainly a description wording issue.

Recommendation: change "applies" to "recommends" or "assesses against."

### TDD boundaries are prompt-only

Files:

- `claude/agents/tdd-red-agent.md`
- `claude/agents/tdd-refactoring-agent.md`

The TDD red agent says it never modifies `app/`, but that boundary is only in prose. The refactoring agent has similarly important phase boundaries.

Recommendation: if the runner supports tool/path restrictions, encode those boundaries in metadata or document that they are prompt-only.

### `view-component-agent` description punctuation

File: `claude/agents/view-component-agent.md`

The description is missing punctuation before "Use":

```text
components Use when creating ViewComponents
```

Recommendation: add a period before "Use."

### `review-agent` duplicate wording

File: `claude/agents/review-agent.md`

The description says "modern Rails patterns and modern conventions."

Recommendation: remove the repeated "modern."

### `security-agent` mentions Devise despite passwordless convention

File: `claude/agents/security-agent.md`

The checklist says "Gems up to date (especially Rails, Devise, etc.)" while local auth guidance generally avoids Devise.

Recommendation: replace with "auth stack/session-related gems."

### `prompt-engineer` model outlier

File: `claude/agents/prompt-engineer.md`

This appears to be the only agent with `model: sonnet` rather than `model: inherit`. This may be intentional, but it should be documented so future normalization does not accidentally change it.

## Skills and Agent Mapping

### Skill Links Are Healthy

All declared `skills:` entries resolve to existing skill folders. No broken skill slugs were found in agent frontmatter.

### High-Value Skills Without Dedicated Agent Coverage

Skills that are not currently preloaded by a dedicated agent include:

- `action-cable-patterns`
- `active-storage-setup`
- `form-object-patterns`
- `hotwire-native-auth`
- `hotwire-native-path-config`
- `i18n-patterns`
- `performance-optimization`
- `rails-architecture`
- `tdd-cycle`

Recommendation:

- Add dedicated agents only where the workflow is common enough to justify it.
- Otherwise document ownership: for example, `rails-expert` owns `rails-architecture`, native agents own Hotwire Native auth/path config, `test-agent` or `implement-agent` owns `tdd-cycle`, and a future performance agent owns `performance-optimization`.

### Agents Without Skills

The following agents have no `skills:` frontmatter and should either preload a relevant skill or be explicitly standalone:

- `compliance-auditor`
- `database-optimizer`
- `frontend-developer`
- `hotwire-native-android-agent`
- `hotwire-native-ios-agent`
- `performance-monitor`
- `postgres-pro`
- `prompt-engineer`
- `rails-expert`
- `security-agent`
- `ui-designer`

Recommendation:

- Prioritize adding skills to Hotwire Native, Rails expert, security, and performance/database agents.
- Leave generic agents standalone only if they intentionally operate outside the Rails skill system.

## Recommended Cleanup Plan

1. Fix safety contradictions first: `compliance-auditor`, `security-agent`, and TDD boundary enforcement.
2. Resolve the authentication architecture conflict between `auth-agent` and `authentication-flow`.
3. Remove or replace `context-manager`, `runSubagent`, and fake collaborator references.
4. Retarget `frontend-developer` to this repo's Hotwire stack, or mark it as SPA-only.
5. Add `skills:` to Hotwire Native agents and consider trimming duplicated content.
6. Update `rails-expert` for Rails 8 and preload `rails-architecture`.
7. Add a shared model/concern/service decision ladder.
8. Update `README.md` with the real agent frontmatter schema.
9. Add a lightweight validator for agents similar to the skills validator:
   - frontmatter parses
   - `name` matches file name
   - declared `skills:` exist
   - no root-level phantom collaborator references
   - read-only agents do not use implementation verbs by default

## Suggested Validation Checks

A repeatable agent validator should check:

- Every file has YAML frontmatter with `name`, `description`, and `model`.
- Agent file basename matches `name`.
- Every declared skill exists under `claude/skills`.
- Read-only agents using `disallowedTools: Write, Edit` do not contain default instructions to implement, deploy, or modify.
- References to `context-manager`, `runSubagent`, and `@agent` names point to real local mechanisms.
- Agent documentation in `README.md` matches the frontmatter fields used in practice.

This would catch most of the current drift before new agents are added.
