# Customizing the Claude Code System Prompt — A Rails Team's Field Guide

*A practical guide to shaping Claude Code's behavior on Ruby on Rails stacks, using official extension points (strongly preferred) and a clear-eyed look at unofficial binary-patching hacks (avoid). Current as of June 2026 / Claude Code v2.1.x. Verify version-specific details against `code.claude.com/docs` and `claude --version`.*

## Table of Contents
1. [The mental model: how the system prompt composes](#the-mental-model-how-the-claude-code-system-prompt-composes)
2. [CLAUDE.md memory files](#1-claudemd-memory-files)
3. [CLI system-prompt flags](#2-cli-system-prompt-flags)
4. [Output styles](#3-output-styles)
5. [Hooks](#4-hooks)
6. [Subagents, slash commands, settings layering](#5-subagents-slash-commands-settings-layering)
7. [Keeping a team consistent (what goes where)](#6-keeping-a-team-consistent-what-goes-where)
8. [Unofficial / "hacky" patching — avoid these](#7-unofficial--hacky-patching-approaches--avoid-these)
9. [Recommendations](#recommendations)
10. [Caveats](#caveats)

---

## TL;DR
- Use the **official layered extension points** — `CLAUDE.md` memory, `.claude/rules/`, output styles, `--append-system-prompt`, hooks, subagents, and `settings.json` — to steer Claude Code; they compose predictably and survive the multiple-releases-a-week cadence (Claude Code went from v2.1.69 to v2.1.101 in roughly five weeks in spring 2026).
- **Unofficial binary/prompt patching (tweakcc, `cli.js` string-replacement, base-URL proxies that rewrite the system prompt) is brittle** — Anthropic's prompt is "500+ strings constantly changing and moving within a very large minified JS file," so patches break on nearly every release; the approach is unsupported and risks ToS/security problems. Every goal it serves has an official equivalent.
- For a Rails team, the **baseline** is: a tight project `CLAUDE.md` + path-scoped `.claude/rules/` for architecture conventions, a RuboCop/RSpec hook for deterministic enforcement, a couple of subagents (migration reviewer, N+1 detector), and committed `.claude/` config so the whole team gets identical behavior.

---

## The mental model: how the Claude Code system prompt composes

Claude Code starts each session with a **base system prompt** authored by Anthropic (tool guidance, safety rules, coding conventions, concise-output instructions). You never edit that file directly through supported means. Several layers compose *around* it:

- **Output styles** are the only official feature that *directly modifies* the system prompt. Custom styles add their instructions to the **end** of the system prompt and, by default, **leave out** Claude Code's built-in software-engineering instructions unless `keep-coding-instructions: true`.
- **`--append-system-prompt`** appends text to the system prompt without removing anything (per-invocation only).
- **`--system-prompt` / `--system-prompt-file`** fully replace the base prompt (headless/SDK-oriented).
- **`CLAUDE.md` is NOT part of the system prompt** — its content is delivered as a *user message* after the system prompt. This is the single most common misconception, and it's why CLAUDE.md is guidance rather than enforcement.
- **Hooks** don't touch the system prompt either, but `UserPromptSubmit` and `SessionStart` hooks can inject text into context, and `PreToolUse` hooks can deterministically block/allow tool calls regardless of what the prompt says.
- **Subagents** run with their own separate system prompt, model, and tools.
- **Permissions/settings** wrap everything as a hard enforcement layer.

### Composition / precedence summary

| Layer | Touches system prompt? | Where it lives | Scope | Enforcement |
|---|---|---|---|---|
| Base prompt | The prompt itself | Bundled in CLI | Every session | n/a |
| Output style | Appends to system prompt (can strip coding instructions) | `~/.claude/output-styles/`, `.claude/output-styles/` | Session (set at start) | Soft (model guidance) |
| `--append-system-prompt` | Appends | CLI flag | One invocation | Soft |
| `--system-prompt(-file)` | Replaces entirely | CLI flag | One invocation (headless/SDK) | Soft |
| `CLAUDE.md` / `.claude/rules/` | No — user message after prompt | project/user/managed | Every session (rules can be path-scoped) | Soft |
| Subagent | Own system prompt | `.claude/agents/`, `~/.claude/agents/` | When delegated | Soft (own tools) |
| Hooks | No — inject context or gate tools | `settings.json` | Lifecycle events | **Hard** (PreToolUse deny, exit 2) |
| Permissions | No | `settings.json` | Always | **Hard** |

A useful framing from Anthropic's docs: output styles are "stored system prompts," slash commands/skills are "stored prompts," and CLAUDE.md is project context delivered as a user message.

---

## 1. CLAUDE.md memory files

### Locations and load order (broadest → most specific)

| Scope | Location | Purpose |
|---|---|---|
| Managed policy | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS), `/etc/claude-code/CLAUDE.md` (Linux/WSL), `C:\Program Files\ClaudeCode\CLAUDE.md` (Windows) | Org-wide; cannot be excluded |
| User | `~/.claude/CLAUDE.md` | Personal prefs across all projects |
| Project | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team-shared, committed |
| Local | `./CLAUDE.local.md` | Personal, gitignored |

**How loading works:** Claude walks *up* the directory tree from the working directory and concatenates every `CLAUDE.md`/`CLAUDE.local.md` it finds (root → cwd order; files closer to where you launched are read last). Files are **additive, not overriding**. Nested CLAUDE.md files in *sub*directories load on demand when Claude reads files there. Across the tree the order is managed → user → project → local.

**Size matters:** Per Anthropic's Memory docs, *"target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."* The `/init` command generates a starter (set `CLAUDE_CODE_NEW_INIT=1` for an interactive multi-phase flow); `/memory` lists and edits loaded files. The `#` inline-memory shortcut was discontinued — use `/memory` or just ask Claude to remember something.

**Imports:** `@path/to/file` syntax expands files into context at launch (relative to the importing file; recursive up to 4 hops; skips code spans/fenced blocks). Imported files still consume context. Claude reads `CLAUDE.md`, not `AGENTS.md` — but you can `@AGENTS.md` import it or symlink.

**Auto memory** (v2.1.59+): Claude writes its own notes to `~/.claude/projects/<project>/memory/MEMORY.md` (first 200 lines / 25 KB loaded each session). Toggle via `/memory` or `autoMemoryEnabled: false`.

### Sample project-root `CLAUDE.md` for a Rails 8 app

```markdown
# CLAUDE.md — Acme (Rails 8 SaaS)

## Stack
- Rails 8, Ruby 3.3, PostgreSQL, Redis (cache + Sidekiq + Action Cable).
- Propshaft + Importmap (NO Node bundler), Thruster, deployed via Kamal.
- Auth: built-in generator — has_secure_password + Session model + Current.
- Testing: RSpec. Run `bin/rspec`; lint with `bin/rubocop`.
- Dev server: `bin/dev`.

## Architecture rules (enforce these)
- Skinny controllers: parse / authorize / delegate / respond only. No business logic.
- Rich models, but extract multi-step / multi-model operations into Service Objects.
- Service Objects live in `app/services/`, expose `.call`, and ALWAYS return a
  `Result` (`app/services/result.rb`) with `success?/failure?/data/error/code`.
- Query Objects (`app/queries/`) for complex reads. Presenters (`app/presenters/`)
  for view formatting. Form Objects (`app/forms/`) for multi-model/wizard forms.
- Authorization via Pundit Policies (`app/policies/`). Reusable UI via
  ViewComponents (`app/components/`). Async via Sidekiq Jobs (`app/jobs/`).
- Concerns in `app/models/concerns` and `app/controllers/concerns` for shared behavior.

## Multi-tenancy (CRITICAL)
- Every query is scoped through the current account: `current_account.events`.
- NEVER write `Event.where(user_id:)` or an unscoped `Model.find`. Always go through
  the tenant association.

## When NOT to abstract
- Don't wrap a single `Model.create` in a service — that's indirection, not abstraction.
- Don't add a Query Object for a one-line scope. Prefer a model scope.
- Reach for a pattern only when logic spans multiple models/externals or is reused.

## Testing by layer
- Models / services / queries / presenters / policies → unit specs.
- Controllers → request specs. Components → component specs. Critical flows → system specs.
- Write a spec for new/changed behavior. Run `bin/rspec` before declaring done.

## Database
- NEVER edit `db/schema.rb` directly — always generate a migration.
- Don't add SPA frameworks; use Hotwire (Turbo + Stimulus).

See @README.md for setup and @docs/architecture.md for the domain model.
```

The `Result` object this references:

```ruby
# app/services/result.rb
class Result
  attr_reader :data, :error, :code

  def initialize(success:, data: nil, error: nil, code: nil)
    @success = success
    @data = data
    @error = error
    @code = code
  end

  def self.success(data = nil)            = new(success: true, data: data)
  def self.failure(error, code: nil)      = new(success: false, error: error, code: code)

  def success? = @success
  def failure? = !@success
end
```

### `.claude/rules/` for path-scoped conventions

Keep the root file small and move topic-specific guidance into `.claude/rules/*.md`. Rules without a `paths:` field load every session; path-scoped rules load only when Claude touches matching files:

```markdown
---
paths:
  - "app/services/**/*.rb"
  - "spec/services/**/*_spec.rb"
---
# Service Object rules
- One public `.call`; class method `.call(...)` delegates to `new(...).call`.
- Return a `Result`. No raising for *expected* failures; let real bugs bubble up.
- Wrap multi-table writes in a transaction; rescue only exceptions you expect.
- Scope all reads/writes through the passed-in `account` (never a global lookup).
```

This is the pattern teams like Planet Argon and thoughtbot use: a short briefing-doc `CLAUDE.md` plus modular, path-scoped rules so a Rails session never loads frontend conventions.

### Global vs per-project split

- `~/.claude/CLAUDE.md` (personal, all projects): "I prefer RSpec's `expect` syntax," "explain trade-offs tersely," "use `bin/` binstubs."
- Project `CLAUDE.md` (committed): the architecture rules above — shared by the whole team.
- `CLAUDE.local.md` (gitignored): "my local sandbox runs on port 3001," WIP landmines like "don't touch `app/models/invoice.rb` yet."

---

## 2. CLI system-prompt flags

| Flag | Effect | Mode |
|---|---|---|
| `--append-system-prompt "..."` | Appends to base prompt; keeps tool guidance + safety | Interactive (since **v1.0.51**) **and** print/`-p` |
| `--append-system-prompt-file ./f.txt` | Same, from a file | Both (community-reported; confirm for your version) |
| `--system-prompt "..."` / `--system-prompt-file` | **Replaces** the entire base prompt | Primarily SDK / `-p` headless |

Appending preserves Claude Code's identity, tool guidance, and safety instructions — use it for "keep acting like Claude Code, but add one rule." Replacement drops everything (including safety/tool guidance), so use it only for non-coding pipeline agents where you own the whole prompt. Both apply only to the current invocation, so they suit scripts/automation better than persistent interactive use.

```bash
# One-off Rails task with an extra house rule (works interactively as of v1.0.51)
claude --append-system-prompt "All new queries must be scoped through current_account; \
flag any unscoped finder as a multi-tenancy bug."

# Headless CI review of a PR diff
gh pr diff 123 | claude -p \
  --append-system-prompt "You are reviewing a Rails 8 PR. Enforce: skinny controllers, \
Service Objects returning Result, Pundit policies, account scoping, specs by layer." \
  --output-format json --allowedTools "Read,Grep" > review.json
```

For persistent personas, use output styles; for project conventions, use CLAUDE.md. (`--append-system-prompt` can also be set org-wide via `appendSystemPrompt` in managed settings.)

---

## 3. Output styles

Output styles **directly modify the system prompt** — the only feature that does. Per the docs: *"All output styles have their own custom instructions added to the end of the system prompt … Custom output styles leave out Claude Code's built-in software engineering instructions … unless `keep-coding-instructions` is set to `true`."*

Built-in styles: **Default**, **Proactive** (acts immediately, fewer pauses), **Explanatory** (adds "Insights"), **Learning** (adds `TODO(human)` markers).

**Recent change to note:** the standalone `/output-style` command was **deprecated in v2.1.73 and removed in v2.1.91**. Set styles via `/config` → Output style, or the `outputStyle` field in `.claude/settings.local.json`. The style is fixed at session start (for prompt-cache stability); changes take effect after `/clear` or a new session. Files live at `~/.claude/output-styles/` (user) or `.claude/output-styles/` (project).

### Custom "Senior Rails reviewer" output style

```markdown
---
name: Senior Rails Reviewer
description: Terse senior-Rails code-review voice; keeps coding ability
keep-coding-instructions: true
---
You review and write code as a senior Rails engineer on this team.

- Lead with the highest-risk issue. Be terse; skip praise.
- Always check: skinny controllers, Service Objects returning a Result,
  account scoping (no unscoped finders), N+1 risk, missing specs.
- Prefer Rails idioms over cleverness. Call out over-engineering explicitly
  ("this service wraps a single create — inline it").
```

### When to use which

- **Output style** — you want a *persistent voice/role every turn* (reviewer, TDD pair). It's session-wide and modifies the prompt at the system level.
- **CLAUDE.md** — *project facts and conventions* Claude should always know. Putting the reviewer persona in CLAUDE.md would consume context as a user message every turn and is weaker than a system-prompt-level style; conversely, putting project architecture in an output style would wrongly strip coding instructions and isn't shareable as durable facts.

---

## 4. Hooks

Hooks are user-defined shell commands (or HTTP/prompt/agent handlers) that fire on lifecycle events. They give **deterministic** control that CLAUDE.md (advisory) cannot. Configure them in `settings.json` under a top-level `hooks` key.

**Settings files (and precedence):** `~/.claude/settings.json` (user) < `.claude/settings.json` (project, committed) < `.claude/settings.local.json` (local, gitignored) < CLI args < enterprise managed settings. Scalars override by precedence; **arrays (including `hooks` and `permissions.allow`) concatenate and dedupe** across layers. Managed settings are the absolute floor.

**JSON structure:** event → array of `{ matcher, hooks: [{ type, command, timeout }] }`. The matcher is an exact tool name, a `|`-list (`Edit|Write`), or a regex; `""`/omitted matches all.

**Key events:**
- `PreToolUse` — before a tool; exit 2 or `permissionDecision: "deny"` blocks it (works even under `--dangerously-skip-permissions`).
- `PostToolUse` — after; can't undo, but can lint/test/feed back.
- `UserPromptSubmit` — stdout is injected as context Claude reads.
- `SessionStart` — stdout injected as context; `source` is startup/resume/clear/compact.
- `Stop` / `SubagentStop` — exit 2 forces Claude to keep working (guard against loops with `stop_hook_active`).
- `PreCompact`, `Notification`, `SessionEnd`.

**Exit codes:** `0` = proceed (stdout parsed as JSON; for `UserPromptSubmit`/`SessionStart`, stdout is added to context); `2` = block, stderr fed back to Claude as feedback; any other = non-blocking error. Use absolute paths or `$CLAUDE_PROJECT_DIR`. Hooks are snapshotted at session start; changes must be reviewed in `/hooks`.

### Rails hook examples

**(a) Auto-RuboCop after editing Ruby files (PostToolUse)** — the common community pattern:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command",
            "command": "jq -r '.tool_input.file_path' | { read f; [[ \"$f\" == *.rb ]] && bin/rubocop -a \"$f\" >&2 || true; }" }
        ]
      }
    ]
  }
}
```

**(b) thoughtbot's approach — a `Stop` gate that runs RuboCop on all touched Ruby files and blocks until clean.** This is from thoughtbot's post *"Enforcing Your Ruby Style Guide on AI-Generated Code."* Note it is a **`Stop`** hook driven by **`git diff`** (not a PostToolUse + jq file-path formatter), it has **no `matcher`**, and it gives Claude exactly one autocorrect-and-retry cycle before surfacing leftovers (using `jq` only to read `.stop_hook_active`):

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [
        { "type": "command",
          "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/rubocop-gate.sh",
          "timeout": 120 }
      ] }
    ]
  }
}
```

```bash
#!/bin/bash
set -uo pipefail
INPUT=$(cat)
cd "$CLAUDE_PROJECT_DIR"

ruby_files() {
  {
    git diff --name-only --diff-filter=AM HEAD -- '*.rb' '*.rake' 'Gemfile' 'Rakefile';
    git ls-files --others --exclude-standard -- '*.rb' '*.rake';
  } | sort -u
}
RUBY_FILES=$(ruby_files)
[ -z "$RUBY_FILES" ] && exit 0

# Second stop attempt: Claude already had one chance to fix. Surface, then allow stop.
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  REMAINING=$(bundle exec rubocop --force-exclusion $RUBY_FILES 2>&1)
  [ $? -ne 0 ] && { echo "RuboCop violations remain after one retry:" >&2; echo "$REMAINING" >&2; }
  exit 0
fi

OUTPUT=$(bundle exec rubocop --force-exclusion --autocorrect $RUBY_FILES 2>&1)
if [ $? -ne 0 ]; then
  echo "RuboCop found violations that could not be auto-corrected. Fix them before completing." >&2
  echo "See .claude/rules/rubocop.md for guidance on judgment-call cops." >&2
  echo "$OUTPUT" >&2
  exit 2
fi
exit 0
```

thoughtbot pairs this with a `.claude/rules/rubocop.md` instructing Claude **never** to silence `Rails/OutputSafety` (XSS) or `ThreadSafety` cops inline, and to *surface rather than refactor* judgment-call cops like `Rails/SkipsModelValidations` and `RSpec/MultipleExpectations`. Their published rules set (TDD, RESTful routes, strong params, RuboCop guidance) lives in the `rails/ai-rules` directory of the `thoughtbot/guides` repo.

**(c) Run the relevant spec after editing a file (PostToolUse):**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/run-spec.sh",
            "timeout": 180 }
        ]
      }
    ]
  }
}
```

```bash
#!/usr/bin/env bash
# .claude/hooks/run-spec.sh — run the matching spec for an edited app file
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[[ -z "$FILE" ]] && exit 0
# app/services/foo.rb -> spec/services/foo_spec.rb
SPEC=$(echo "$FILE" | sed -E 's#^app/#spec/#; s#\.rb$#_spec.rb#')
[[ -f "$SPEC" ]] || exit 0
bin/rspec "$SPEC" 2>&1 | tail -20
exit 0
```

**(d) Block edits to `db/schema.rb` and secrets (PreToolUse):**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command",
            "command": "f=$(jq -r '.tool_input.file_path // empty'); echo \"$f\" | grep -qE 'db/schema\\.rb$|\\.env|config/credentials' && { echo 'Blocked: generate a migration / never edit secrets directly' >&2; exit 2; } || exit 0" }
        ]
      }
    ]
  }
}
```

**(e) Inject Rails context at session start (SessionStart):**

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [
        { "type": "command",
          "command": "echo \"Rails: $(bin/rails --version 2>/dev/null) | Branch: $(git branch --show-current) | Recent migrations: $(ls db/migrate | tail -3)\"" }
      ] }
    ]
  }
}
```

stdout from `SessionStart`/`UserPromptSubmit` is injected as context Claude can read. You could also dump a routes or schema summary here.

**(f) Enforce the account-scoping convention (UserPromptSubmit):** inject a standing reminder before every prompt:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [
        { "type": "command",
          "command": "echo 'Reminder: scope every query through current_account; flag unscoped finders as multi-tenancy bugs.'" }
      ] }
    ]
  }
}
```

**Security & performance:** hooks run with your credentials — never run untrusted scripts; quote variables; keep hot-path hooks fast. Pair heavy tools (full suite, full RuboCop) with infrequent events like `Stop` or pre-push, not every `Edit`. Note a known issue: a `PostToolUse` formatter that rewrites the file Claude just wrote can have its changes silently overwritten in some versions — prefer surfacing fixes for Claude to apply, or use the `Stop`-gate pattern above.

---

## 5. Subagents, slash commands, settings layering

### Subagents (`.claude/agents/`)

Markdown + YAML frontmatter; the body **is** the subagent's system prompt. They run in an isolated context with their own model and tools. Project agents (`.claude/agents/`, committed) are team specialists; user agents (`~/.claude/agents/`) are personal; project wins on a name collision. Use `proactively`/`PROACTIVELY` in the description to let Claude auto-delegate; restrict `tools` to least privilege (a read-only reviewer can't accidentally edit).

```markdown
---
name: rails-migration-reviewer
description: Reviews Rails migrations for safety. Use proactively whenever a file under db/migrate is created or changed.
tools: Read, Grep, Glob, Bash
model: sonnet
---
You are a senior Rails engineer reviewing a database migration.
Check for: NOT NULL columns added without a backfill/default; indexes added without
`algorithm: :concurrently` (+ `disable_ddl_transaction!`); renaming/removing columns
in a single deploy (use a safe multi-step migration); missing foreign keys; and lock
risk on large tables. Confirm the change will be reflected via a generated
`db/schema.rb` (never hand-edited). Report findings by severity with a concrete safer rewrite.
```

```markdown
---
name: n1-query-detector
description: Detects N+1 query risks in Rails code and specs. Use proactively after editing models, queries, controllers, or views.
tools: Read, Grep, Glob, Bash
model: sonnet
---
You hunt N+1 queries. Inspect recently changed code for iteration over an
association without `includes/preload/eager_load`. Suggest the minimal eager-load
fix plus a Bullet-style assertion or request spec that catches the regression.
Confirm queries are scoped through current_account.
```

### Slash commands / skills (`.claude/commands/`)

`.claude/commands/*.md` (project) and `~/.claude/commands/*.md` (personal) define `/name` prompts. As of **v2.1.101**, custom commands were **merged into Skills** (`.claude/skills/<name>/SKILL.md`); both formats still work, and a skill wins if names collide. Commands support frontmatter (`description`, `allowed-tools`, `argument-hint`), `$ARGUMENTS`, `@file` references, and `` !`command` `` pre-execution.

```markdown
---
description: Scaffold a Service Object + RSpec spec following team conventions
argument-hint: <Namespace::ServiceName>
allowed-tools: Write, Read
---
Create a service object at `app/services/$ARGUMENTS.rb` and a matching spec at
`spec/services/$ARGUMENTS_spec.rb`.

Requirements (see @CLAUDE.md):
- Single public `.call`; class method `.call(...)` delegates to `new(...).call`.
- Return a `Result` (`app/services/result.rb`) — success?/failure?/data/error/code.
- Scope all reads/writes through the passed-in `account` (no global lookups).
- Wrap multi-table writes in a transaction; rescue only expected exceptions.
- Spec covers: success path, expected-failure path, and one edge case.
```

### Settings precedence (full picture)

Enterprise **managed** (`managed-settings.json`, MDM/registry/server-push) → **CLI args** → **local** (`.claude/settings.local.json`) → **project** (`.claude/settings.json`) → **user** (`~/.claude/settings.json`). Managed always wins and cannot be overridden — ideal for `permissions.deny` of secret reads/destructive commands. Within permissions, **deny > ask > allow**, strictest match wins. `claudeMd` and `appendSystemPrompt` can even be set in managed settings for org-wide behavior. Run `/status` to see which setting sources are active.

---

## 6. Keeping a team consistent (what goes where)

| Goal | Mechanism | Commit? |
|---|---|---|
| Architecture conventions everyone shares | project `CLAUDE.md` + `.claude/rules/` | Yes (`.claude/` in git) |
| Personal prefs | `~/.claude/CLAUDE.md`, `CLAUDE.local.md` | No (gitignore local) |
| Persistent reviewer/TDD voice | output style (project `.claude/output-styles/`) | Yes |
| One-off task rule / CI run | `--append-system-prompt` | n/a (in script/CI) |
| Deterministic lint/test/guardrails | hooks in `.claude/settings.json` | Yes |
| Personal/experimental hooks | `.claude/settings.local.json` | No |
| Specialist reviewers | `.claude/agents/` | Yes |
| Scaffolding workflows | `.claude/commands/` or `.claude/skills/` | Yes |
| Org-wide hard policy | managed `settings.json` + managed `CLAUDE.md` | Deployed by IT |

`.gitignore` should include `CLAUDE.local.md` and `.claude/settings.local.json`; commit `.claude/CLAUDE.md`, `.claude/rules/`, `.claude/agents/`, `.claude/commands/`, `.claude/output-styles/`, and the shared `.claude/settings.json`.

---

## 7. Unofficial / "hacky" patching approaches — avoid these

These exist; they are **brittle, unsupported, and strongly discouraged**. Each is listed with why it breaks and the official replacement.

### tweakcc and `cli.js` string-replacement
Tools like **tweakcc** (`npx tweakcc`) and hand-rolled `patch-claude-code.sh` scripts edit the bundled, minified `cli.js` (or extract/repack the native binary) to rewrite Anthropic's actual system-prompt strings — e.g., flipping "be brief" into "be thorough." Community repos like `claude-code-system-prompts` and `tweakcc-system-prompts-unnerfed` distribute modified prompt sets.

**Why brittle:**
- Anthropic's prompt is **"500+ strings that are constantly changing and moving within a very large minified JS file."** Target strings move or disappear on nearly every release — e.g., v2.1.100 removed the brevity instructions the patches targeted.
- tweakcc itself ships *"verified to work with"* a specific pinned Claude Code version and warns that on newer/earlier versions *"various patches might not work."* Your customizations are *"overwritten"* on every update and must be re-applied.
- The **v2.1.113 switch to a native binary** broke the npm-`cli.js` patch entirely; users had to deliberately downgrade to npm installs to keep patching.
- It reproduces Anthropic's copyrighted prompt text, may run afoul of ToS, and keeps you off the auto-updating native binary — which silently delivers **security patches** (Anthropic shipped 30+ security-relevant fixes between April and June 2026).
- It's impossible to keep consistent across a team.

**Official replacement:** output styles (to alter voice/verbosity at the system-prompt level), `--append-system-prompt`, and CLAUDE.md/rules. If you want "more thorough" output, a custom output style with `keep-coding-instructions: true` achieves it supportedly.

### Proxy/middleware interception (`ANTHROPIC_BASE_URL`)
Pointing `ANTHROPIC_BASE_URL` at a local proxy (mitmproxy, LiteLLM-based `claude-code-proxy`, cli-proxy-api, enterprise gateways) lets you log, reroute, or in principle **rewrite the outbound request body — including the system prompt** — before it reaches Anthropic.

**Why brittle (for prompt-rewriting specifically):** you're mutating an undocumented request shape that changes frequently; you must preserve tool-use IDs and SSE streaming or multi-turn tool calls break; Claude-specific features (cache control, extended thinking) may not round-trip; and the variable is read **once at process start**, so changing it mid-session silently does nothing. There are also reports of Anthropic flagging certain proxy keywords as billing/access anomalies.

**Legitimate uses of the same knob:** routing through a corporate **gateway** for observability, cost control, or multi-provider access is a reasonable, documented enterprise pattern — just don't use it to rewrite the system prompt. For that, use the official extension points.

### Wrapper scripts / env tricks
A shell alias that always injects `--append-system-prompt` is fine and *officially supported* — that's just automation. The anti-pattern is wrappers that depend on patched binaries or rewrite internal state.

**Bottom line:** every hacky method maps to an official extension point. Prefer the official one — it survives the weekly updates, keeps security patches flowing, and is reproducible across a team.

---

## Recommendations

**Stage 1 — Baseline (any Rails team, ~30 min):**
1. Run `/init`, then trim the generated `CLAUDE.md` to <200 lines using the Rails 8 template above (architecture rules, multi-tenancy, when-not-to-abstract, testing-by-layer, "never edit schema.rb").
2. Add a `.claude/settings.json` with one RuboCop hook (PostToolUse autocorrect or the thoughtbot `Stop`-gate) plus a `PreToolUse` guard blocking `db/schema.rb`/secrets. Commit `.claude/`. Add `CLAUDE.local.md` and `.claude/settings.local.json` to `.gitignore`.

**Stage 2 — Conventions as code (~1 hr):**
3. Move topic-specific guidance into path-scoped `.claude/rules/` (services, queries, policies, components, jobs).
4. Add a `Stop` hook (or `PostToolUse` run-spec script) that runs the relevant `bin/rspec` for changed files.
5. Add a `/new-service` command (and `/new-policy`, `/new-component`) scaffolding the file + spec to team conventions.

**Stage 3 — Specialists & team scale:**
6. Add `rails-migration-reviewer` and `n1-query-detector` subagents with `proactively` descriptions and least-privilege tools.
7. Adopt the "Senior Rails Reviewer" output style for review sessions.
8. If you're an org: deploy a managed `settings.json` denying secret reads/destructive Bash and a managed `CLAUDE.md` with compliance reminders.

**Thresholds that change the plan:**
- CLAUDE.md creeping over ~200 lines → split into `.claude/rules/` immediately.
- Hooks adding noticeable latency → move heavy checks off `Edit`/`Write` to `Stop`/pre-push.
- Repeated identical corrections in chat → promote to CLAUDE.md or a rule.
- Tempted to patch the binary → that's the signal to reach for an output style or `--append-system-prompt` instead.

---

## Caveats
- **Claude Code changes weekly.** The output-style command removal (`/output-style` gone in v2.1.91, replaced by `/config`), the commands→skills merger (v2.1.101), and the npm→native-binary default (v2.1.113) are all recent. Verify against official docs (`docs.claude.com` / `code.claude.com/docs`) for your installed version (`claude --version`).
- **CLAUDE.md is guidance, not enforcement.** It's delivered as a user message; Claude can deviate, especially on vague or conflicting instructions. For hard guarantees (block schema edits, force tests) use hooks/permissions.
- The thoughtbot hook example is a **`Stop`** hook driven by `git diff` — a different pattern from the common PostToolUse + `jq` formatter; both are shown. There's also a known issue where PostToolUse file modifications can be silently overwritten in some versions.
- Don't commit secrets in `.claude/` config; HTTP-hook tokens belong in environment variables referenced via `allowedEnvVars`.
- Community blogs vary in accuracy and some cite unconfirmed flags (`--append-system-prompt-file`, `-n`/`-r`, `--worktree`); treat non-Anthropic sources as secondary and confirm against official docs.
- Avoid bloated CLAUDE.md files (they reduce adherence), conflicting instructions across layers (Claude may pick arbitrarily), and hooks that run untrusted code or slow the loop — these are the most common self-inflicted failure modes.
