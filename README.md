# AI-BANK

A centralized repository of AI tooling resources -- skills, agents, rules, Dockerfiles, templates, and guides -- for AI-powered development with Cursor, Claude Code, and OpenAI Codex.

---

## Table of Contents

**Concepts**
- [What are Skills?](#what-are-skills)
- [What are Agents?](#what-are-agents)
- [What are Rules?](#what-are-rules)
- [What are AGENTS.md and CLAUDE.md files?](#what-are-agentsmd-and-claudemd-files)
- [What is MCP?](#what-is-mcp-model-context-protocol)
- [Favorite MCPs](#favorite-mcps)

**Tools**
- [Claude Code](#claude-code)
- [OpenAI Codex](#openai-codex)
- [Cursor](#cursor)
- [Cursor Cloud Agents](#cursor-cloud-agents)

**Best Practices**
- [Using AI Agents Efficiently](#using-ai-agents-efficiently)
- [Managing Context](#managing-context)
- [Cloud Agent Best Practices](#cloud-agent-best-practices)
- [Subagent Best Practices](#subagent-best-practices)
- [Unique Cursor Features to Leverage](#unique-cursor-features-to-leverage)

**Repository Catalog**
- [Directory Structure](#directory-structure)
- [MCP Server](#mcp-server)
- [Codex Catalog](#codex-catalog)
- [Claude Skills](#claude-skills)
- [Claude Agents](#claude-agents)
- [Claude Commands](#claude-commands)
- [Claude Rules](#claude-rules)
- [Cursor Rules](#cursor-rules)
- [Templates](#templates)
- [Docker](#docker)
- [Resources and Documentation](#resources-and-documentation)

**Usage**
- [Getting Started](#getting-started)
- [Contributing](#contributing)

---

## Concepts

### What are Skills?

Skills are modular, self-contained packages that extend an AI agent's capabilities by providing specialized knowledge, workflows, and reusable resources. Think of them as onboarding guides for a specific domain -- they transform a general-purpose agent into a specialized expert equipped with procedural knowledge it could not fully possess on its own.

A skill lives in a named directory and consists of:

```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + instructions
├── scripts/          # Optional: executable scripts for deterministic tasks
├── references/       # Optional: documentation loaded into context as needed
└── assets/           # Optional: templates, images, and files used in output
```

**SKILL.md** has two parts:
- **Frontmatter** (`name`, `description`) -- always in context and used to decide when to trigger the skill
- **Body** (markdown instructions) -- loaded only after the skill is triggered

Skills use progressive disclosure to stay context-efficient. The metadata (~100 words) is always present. The body (<5k words) loads on trigger. Reference files load only when Claude determines they are needed. This keeps the context window lean for the common case.

**When to use a skill:** When a task involves domain-specific procedural knowledge, reusable scripts, or reference material that would otherwise need to be re-explained every session.

See all available skills in the [Claude Skills](#claude-skills) catalog below. See [`claude/skills/skill-creator/`](claude/skills/skill-creator/) for guidance on creating new ones.

---

### What are Agents?

Agents are specialized AI personas defined in markdown files with YAML frontmatter. Each agent has a defined name, description, model, and a detailed system prompt that establishes its expertise, philosophy, and behavioral constraints for a specific domain.

An agent definition looks like this:

```markdown
---
name: test-agent
description: Writes Minitest tests, integration tests, and fixtures (not factories)
model: inherit
color: green
---

# Test Agent

You are an expert Rails testing specialist...
```

Agents differ from skills in a key way: a skill extends what an agent *knows*, while an agent defines *who the agent is*. An agent can use multiple skills. In Claude Code, agents can also spawn subagents -- calling other agents to handle focused subtasks within a larger workflow.

The `implement-agent` in this repository demonstrates orchestration: it delegates to 19 specialized agents in a defined dependency order (database → models → controllers → views → jobs → tests) rather than generating everything itself.

**When to use an agent:** When a task is complex enough to benefit from a focused persona, or when you want a consistent, reusable specialist for a recurring domain (code review, security audits, migrations, etc.).

See all available agents in the [Claude Agents](#claude-agents) catalog below.

---

### What are Rules?

Rules are persistent behavioral instructions that automatically inject into an AI agent's context based on file patterns. They are stored as markdown files with YAML frontmatter and eliminate the need to repeat project conventions in every conversation.

Both **Claude Code** and **Cursor** support rules, with slightly different formats:

**Claude Code rules** live in `.claude/rules/` and use `paths:` for activation:

```markdown
---
paths:
  - "app/models/**/*.rb"
  - "test/models/**/*.rb"
---

# Model Conventions

Always use UUIDs as primary keys...
```

**Cursor rules** live in `.cursor/rules/` and use `globs:` and `alwaysApply:`:

```markdown
---
description: Scope Sentinel - Contract compliance and risk management
globs:
alwaysApply: true
---

# Scope Sentinel

You are operating as a senior consulting team...
```

Rules differ from CLAUDE.md/AGENTS.md in that they support conditional activation based on file patterns. A rule for `app/models/**` only activates when you are working in model files. This keeps irrelevant rules out of the context window.

**When to use a rule:** For persistent, project-wide conventions (security standards, scope management, coding style) or domain-specific guidance that should activate automatically for certain file types.

See all available rules in the [Claude Rules](#claude-rules) and [Cursor Rules](#cursor-rules) catalogs below.

---

### What are AGENTS.md and CLAUDE.md files?

`CLAUDE.md` and `AGENTS.md` are persistent configuration files that act as a project rulebook for AI coding agents. They are automatically loaded at the start of every session, providing consistent context without requiring you to repeat instructions.

- `CLAUDE.md` is used by **Claude Code**
- `AGENTS.md` is used by **OpenAI Codex** and other agents; it is also recognized by Claude Code as a fallback

**What to put in them:**
- Technology stack and architecture decisions
- Coding conventions (naming, indentation, patterns to use or avoid)
- Key commands (`bin/dev`, `rails test`, `bundle exec rubocop`)
- Allowed and forbidden file paths
- Project-specific terminology and domain knowledge

**Placement hierarchy** (more specific files take precedence):

| Location | Scope |
|---|---|
| `~/.claude/CLAUDE.md` | All projects (global defaults) |
| `CLAUDE.md` at project root | Entire project |
| `app/models/CLAUDE.md` | That directory and below |

A template for CLAUDE.md is available at [`claude-md-templates/CLAUDE-TEMPLATE.md`](claude-md-templates/CLAUDE-TEMPLATE.md).

**Pro tip:** Use `/init` in Claude Code or Codex to auto-generate a starter file by having the agent analyze your project structure.

---

### What is MCP (Model Context Protocol)?

MCP is an open standard that connects AI applications to external data sources and tools. It works like a universal adapter -- instead of building a custom integration for every tool, you implement MCP once and gain access to a growing ecosystem of servers.

**Architecture:**

```
Host (Cursor / Claude Code)
  └── MCP Client
        └── MCP Server ── External System (GitHub, DB, filesystem, APIs)
```

The protocol uses JSON-RPC 2.0 and defines three primitives that servers can expose:
- **Resources** -- data to read (files, database records, API responses)
- **Tools** -- actions to invoke (create PR, run query, send message)
- **Prompts** -- reusable prompt templates

**Capabilities:**
- Connect agents to databases, APIs, local filesystems, and SaaS tools
- Access live, up-to-date data rather than static context
- Build composable integrations (one server can chain to others)
- 3,000+ community-built servers available (GitHub, Sentry, Slack, Postgres, etc.)

**Benefits:**
- Eliminates custom integration code for each tool
- Standardized security contracts and audit trails
- Reduces context window usage by fetching only what is needed
- Works across Claude Code, Cursor, Codex, and any MCP-compatible host

**Limitations:**
- Each MCP server is a potential attack surface -- locally running servers have filesystem and network access
- Requires security architecture: least-privilege tools, authorization controls, approval workflows
- Enterprise deployments need governance: audit trails, rate limiting, gateway patterns
- Context window constraints still apply -- fetched data counts against your token budget

**Security note:** Running MCP servers locally without isolation gives them broad access to your machine. See the guide at [`resources/mcp/guides/securing_local_MCP_servers_with_docker.md`](resources/mcp/guides/securing_local_MCP_servers_with_docker.md) for how to sandbox MCP servers with Docker.

### This repo ships its own MCP server

This repository includes a read-only MCP server that exposes its own Skills, Agents, and Rules to any MCP client -- so an agent can `search` and fetch assets on demand instead of copying files. See [MCP Server](#mcp-server) under Repository Catalog for the tool reference, transports, security model, and setup.

### Favorite MCPs

- [`context7`](https://context7.com/)
- [`firecrawl`](https://docs.firecrawl.dev/mcp-server)
- [`figma-mcp`](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server)
- [`github-mcp`](https://github.com/github/github-mcp-server)
- [`code graph context`](https://github.com/CodeGraphContext/CodeGraphContext)
- [`postgresql-mcp`](https://github.com/crystaldba/postgres-mcp)

---

## Tools

### Claude Code

Claude Code is Anthropic's agentic command-line coding tool. It runs in your terminal and can read your codebase, write and edit files, execute shell commands, manage git workflows, and spawn subagents for complex multi-step tasks.

**Capabilities:**
- Full codebase read/write with persistent session context
- Subagent system for task decomposition (specialized agents with isolated context windows)
- Hook system for deterministic automation (linting, formatting, security checks on every operation)
- MCP integration for connecting to external tools and data sources
- Layered permission system gating file access and command execution
- Configuration hierarchy: global `~/.claude/`, project-level `CLAUDE.md`, subfolder overrides
- Model routing: Haiku for fast exploration, Sonnet for general work, Opus for complex reasoning
- Slash commands (`/add-agent`, `/skills`, custom workflow commands)
- Works in terminal, VS Code, and the Claude desktop app

**Benefits:**
- Deep codebase understanding across large repositories
- Hooks guarantee certain operations always run regardless of model behavior
- Subagents keep complex tasks from polluting the main context window
- CLAUDE.md provides persistent, session-to-session consistency
- Strong privacy controls -- opt out of training; API usage never trains models by default

**Limitations:**
- Terminal-first UX requires comfort with CLI workflows
- Agentic operations on large codebases can be slow and expensive
- Hooks and permissions require upfront configuration to be effective
- Context window still limits what can be held in a single session

**Compliance:** SOC 2 Type II, ISO 27001, ISO 42001, HIPAA (with BAA).

---

### OpenAI Codex

OpenAI Codex is a terminal-based AI coding agent built in Rust. It functions as an AI pair programmer with direct read, write, and execution access to your local codebase, with support for multi-agent workflows via the OpenAI Agents SDK and MCP.

**Capabilities:**
- Direct file read/write and shell command execution
- Interactive terminal UI for approving or rejecting individual steps
- Multi-agent coordination via the Agents SDK (parallel agents on the same repo)
- Can expose itself as an MCP server for integration into larger pipelines
- Slash commands: `/model`, `/permissions`, `/agent`, `/mcp`, `/plan`, `/personality`
- Session continuity with `-c` flag for resuming previous sessions
- Configurable via `AGENTS.md` (persistent instructions) and `config.toml` (user-level settings)
- Custom subagents via TOML files in `.codex/agents/` or `~/.codex/agents/`
- Skills via `SKILL.md` packages installed into a Codex skill root
- Sandbox modes and approval policies for controlling agent autonomy

**Benefits:**
- Runs entirely locally with full system access
- Tight integration with OpenAI's model ecosystem (o3, o4-mini, GPT-4o)
- Auditable handoffs with full action traces across multi-agent workflows
- API usage never trains on your data by default

**Limitations:**
- Newer tool with a smaller community and fewer integrations than Cursor or Claude Code
- Multi-agent coordination requires familiarity with the Agents SDK
- Terminal-only interface -- no native IDE integration
- Less mature skill/rule ecosystem compared to Claude Code

---

### Cursor

Cursor is an AI-native code editor built on VS Code with deep AI integration throughout the development experience. It goes beyond inline suggestions to offer a full agent mode capable of reading, writing, and reasoning across your entire codebase.

**Capabilities:**
- Agent mode for autonomous multi-file edits with tool use
- Tab autocomplete with multi-line and pattern-aware predictions
- Inline edit (`Cmd+K`) for targeted, in-place transformations
- Chat panel for codebase-wide Q&A and code generation
- Rules system (`.cursor/rules/`) with glob-pattern activation
- MCP server integration for external tool access
- `.cursorignore` for excluding sensitive files from indexing
- Plan mode (`Shift+Tab`) for approval-gated implementation plans
- YOLO mode for fully autonomous agent execution without approval prompts
- Background/cloud agents for parallel, non-blocking tasks
- Codebase indexing for semantic search across large repositories
- Privacy Mode preventing code from being used for training

**Benefits:**
- Familiar VS Code interface with no workflow disruption
- Rules and AGENTS.md provide persistent, project-aware context
- Plan mode prevents agents from running ahead of your intent
- Privacy Mode available on all tiers including Free
- First-class support for monorepos and large codebases
- Strong community with extensive documentation and tips

**Limitations:**
- Sends recently viewed files and conversation history to Cursor servers (mitigated by Privacy Mode)
- Cloud agents require Pro subscription ($20/month) with usage-based pricing
- Agent mode can be slower than expected on very large codebases
- Rule and context system has a learning curve for new users

**Compliance:** SOC 2 Type II, GDPR, CCPA.

For privacy configuration guidance, see [`resources/documentation/ai_usage.md`](resources/documentation/ai_usage.md).

---

### Cursor Cloud Agents

Cursor Cloud Agents (also called Background Agents) are cloud-powered virtual machines that run AI agents independently of your local machine. They clone your repository into an isolated environment, execute tasks, and produce pull requests -- all without blocking your local workflow.

**Capabilities:**
- Run multiple agents in parallel on isolated tasks simultaneously
- Each agent operates in a full development environment (your Dockerfile defines the environment)
- Create merge-ready pull requests with demo artifacts (screenshots, videos, logs)
- Accessible from the Cursor editor, cursor.com/agents, web, mobile, Slack, and GitHub
- Can navigate web pages, run tests, and resolve complex multi-step issues autonomously
- Over 30% of Cursor's own internal PRs are created by cloud agents

**Benefits:**
- Non-blocking -- agents work while you continue your own tasks
- Reproducible environments via Docker mean agents have the same toolchain as production
- Parallel execution dramatically compresses calendar time on independent tasks
- No local resource consumption for long-running tasks

**Limitations:**
- Requires Pro subscription with usage-based pricing or a minimum monthly spend
- Quality depends heavily on how well the task is scoped and specified upfront
- Generated PRs still require thorough human review before merging
- Debugging a cloud agent that went wrong requires reading logs rather than watching it live
- Environment setup (Dockerfile) requires upfront investment

The Dockerfile in this repository at [`cursor/docker/Dockerfile`](cursor/docker/Dockerfile) provides a production-ready environment for Rails 8.1.1 + PostgreSQL 18 + Redis + Node.js 20 that can be used directly with Cursor Cloud Agents.

---

## Best Practices

### Using AI Agents Efficiently

**Start with a plan, not code.** Use Plan mode in Cursor (`Shift+Tab`) or ask Claude Code to outline its approach before executing. Review and edit the plan before approving. Catching a wrong direction at the plan stage is seconds of work; catching it after 50 file edits is minutes or hours.

**Write specific, bounded prompts.** Vague requests produce vague results. Tell the agent what to build, what patterns to follow, what files are relevant, and what it should not change. The more precise your input, the more predictable the output.

**Let agents search for context.** Rather than manually tagging every relevant file with `@`, ask the agent to explore the codebase and find what it needs. Agents are good at this, and over-loading context with files you think are relevant often produces worse results than letting the agent reason about what matters.

**Revert and refine instead of chasing fixes.** If an agent takes a wrong path, revert its changes and provide a better prompt rather than issuing a series of corrective follow-ups. Follow-up corrections layer context and confusion; a clean restart with better instructions almost always produces better code.

**Use test-driven prompts.** Ask agents to write tests first, then implementation. This forces specificity (tests define exact expected behavior), catches hallucinated APIs, and produces verifiable output. In Cursor, combine this with YOLO mode for fully autonomous test-then-implement loops.

**Break large tasks into checkpoints.** Long tasks accumulate errors. A mistake made at step 3 that goes unnoticed compounds through steps 4-10. Structure complex features as a sequence of smaller tasks, each with a review gate.

**Treat agent output as a first draft.** AI-generated code contains security vulnerabilities at a rate of 25-40% in studies. Review generated code before committing, especially for authentication, payments, and data access.

---

### Managing Context

**Context is a shared, finite resource.** Every token of context used by system prompts, rules, skill bodies, conversation history, and tool results reduces what is available for actual work. Design context intentionally.

**Use progressive disclosure in skills and rules.** Put only what is essential in the always-loaded layer (frontmatter, short descriptions). Put procedural instructions in the body. Put detailed reference material in separate files that load only when needed.

**Keep CLAUDE.md and AGENTS.md lean.** These files load on every session. Include project-specific context that the agent cannot infer itself: stack, patterns, key commands, and conventions. Avoid repeating things the model already knows (e.g., general Rails best practices).

**Use `.cursorignore` and `.gitignore` to exclude noise.** Files in these ignore lists are excluded from Cursor's codebase index. Keep generated files, build artifacts, `node_modules`, large binary assets, and sensitive configuration out of the index.

**Scope reference files by domain.** Rather than one large reference document, organize reference material into domain-specific files (`finance.md`, `sales.md`, `security.md`). Agents load only the files relevant to the current task, keeping context tight.

**Avoid deeply nested reference chains.** Keep reference files one level deep from the SKILL.md. All reference files should link directly from the skill, not from other reference files. Deep nesting obscures what is available and makes context management harder.

**Restart sessions for unrelated tasks.** Conversation history from a previous task is rarely useful for a new one and always costs tokens. Start a fresh session for each distinct task.

---

### Cloud Agent Best Practices

**Scope tasks tightly before starting.** Cloud agents do best with well-bounded, independently executable tasks. "Fix the N+1 query in the projects index action" works far better than "improve app performance." Use a plan phase in your editor first, then delegate the implementation to a cloud agent.

**Provide a working Dockerfile.** Cloud agents run in the environment you define. A Dockerfile that matches your local development setup -- with the right Ruby version, database, test dependencies, and Chromium for system tests -- is the difference between an agent that can run your full test suite and one that cannot verify its own work. See [`cursor/docker/Dockerfile`](cursor/docker/Dockerfile) for a Rails reference.

**Use agents for parallelizable work.** Cloud agents shine when multiple independent tasks can run simultaneously. Bug fixes, feature slices, and test coverage gaps are all good candidates. Tightly coupled work that requires coordination is better done in your local editor.

**Set up proper security boundaries.** Do not give cloud agents production database credentials or secrets with write access to production systems. Use separate identities, staging credentials, and read-only access where possible. Treat cloud agents like external contractors with scoped access.

**Review PRs thoroughly before merging.** Cloud-generated PRs are starting points, not finished products. Review for correctness, security vulnerabilities, edge cases, and adherence to your team's patterns before merging. The agent's speed in producing a PR is valuable; the human review remains non-negotiable.

**Monitor resource usage.** Cloud agent sessions are usage-billed. Set spending limits, avoid open-ended tasks that could run indefinitely, and check the control panel regularly for long-running sessions.

---

### Subagent Best Practices

**Decompose, do not monolith.** Complex features should be broken into component tasks -- database, model, controller, views, tests -- each delegated to a specialized agent. A single agent attempting all layers at once produces less consistent output than an orchestrator coordinating specialists.

**Exploit context isolation.** Each subagent starts with a clean context window. This is a feature, not a limitation. Use it deliberately: give each subagent only the information it needs for its task. The orchestrator maintains the overall plan; subagents execute focused slices.

**Compress results, not processes.** Subagents should return concise summaries of what they accomplished, not full transcripts of their intermediate reasoning. The orchestrator needs to know what was done and what files were created -- not every step taken.

**Run independent tasks in parallel.** Tasks with no dependency on each other can and should run simultaneously. Migration creation, test file generation, and documentation updates often have no ordering dependency. Parallelism reduces wall-clock time dramatically.

**Assign single responsibilities.** Resist the temptation to give a subagent multiple unrelated tasks. A subagent responsible for both creating a migration and updating documentation will do both less well than two focused subagents doing one each.

**Enforce dependency order.** When tasks do depend on each other, enforce sequencing: database schema before models, models before controllers, controllers before views. The `implement-agent` in this repo formalizes this order for Rails feature work.

**Validate at integration.** After subagents complete their pieces, the orchestrating agent should verify that outputs are consistent: naming conventions match, account scoping is present throughout, tests cover the right behaviors.

---

### Unique Cursor Features to Leverage

**Rules with glob patterns** -- The `.cursor/rules/` directory supports multiple rule files, each with YAML frontmatter. Use `globs` to activate rules only when working in relevant files (e.g., a HIPAA rule that activates only for `app/models/**` and `app/controllers/**`). Use `alwaysApply: true` for rules that should always be active (e.g., scope management, security baselines). This is more powerful than a single `.cursorrules` file because rules compose and activate contextually.

**Plan mode** -- Press `Shift+Tab` to switch the agent into Plan mode. The agent will outline its complete implementation plan -- file paths, changes, approach -- before writing a single line of code. You can read, edit, and approve the plan directly in markdown before execution begins. This prevents runaway agents and surfaces assumptions early.

**YOLO mode** -- Enable YOLO mode for the agent to execute autonomously without pausing for approvals. Best combined with test-driven prompts: tell the agent to write tests first, then implement, then verify all tests pass. The test suite acts as the approval gate instead of manual confirmation at each step.

**`.cursorignore`** -- Controls which files are excluded from Cursor's codebase indexing. Files in `.gitignore` are automatically excluded; add additional paths in `.cursorignore` for Cursor-specific exclusions. Keep generated files, build artifacts, and sensitive configuration out of the index to prevent irrelevant context from polluting agent responses.

**MCP server integration** -- Cursor supports Model Context Protocol servers for connecting agents to external tools. Connect to GitHub (for PR creation and issue management), your database (for schema inspection and query running), Sentry (for error context), and more. MCP servers turn agents from code editors into workflow orchestrators.

**Background agents from anywhere** -- Cloud agents can be initiated from the Cursor editor, the web interface at cursor.com/agents, mobile, Slack, and GitHub. This means a developer or project manager can kick off a well-defined task from Slack without opening the editor, and review the resulting PR when it is ready.

**Codebase indexing** -- Cursor indexes your entire repository for semantic search. Agents can find relevant code by meaning, not just by file name or exact text match. This is particularly powerful for large codebases -- ask "where is account scoping enforced?" and the agent will find the relevant code without you knowing the exact file.

**Privacy Mode** -- Available on all tiers including Free. When enabled, your code is not stored or used for model training. On the Business tier it is on by default. Enable it in Settings → Privacy. This is the most important configuration step for protecting intellectual property.

---

## Repository Catalog

### Directory Structure

```
ai-bank/
├── codex/
│   ├── agents/          # 42 Codex custom subagent TOML files
│   ├── rules/           # 33 AGENTS.md templates scoped by directory
│   ├── scripts/         # Transposition and validation scripts
│   └── skills/          # 42 Codex-compatible skill packages
├── claude/
│   ├── agents/          # 42 specialized agent definitions
│   ├── commands/        # 6 workflow slash commands
│   ├── rules/           # 20 path-activated Claude Code rules
│   └── skills/          # 42 domain-specific skills with reference materials
├── claude-md-templates/ # Reusable CLAUDE.md templates
├── cursor/
│   ├── docker/          # Dockerfile for Cursor Cloud Agent environments
│   └── rules/           # 7 context-aware Cursor rules
├── resources/
│   ├── documentation/   # AI usage and privacy guides
│   └── mcp/             # MCP security guides
└── server/              # Read-only MCP server (Python/FastMCP) exposing the catalog
```

---

### MCP Server

The [`server/`](server/) directory is a read-only **MCP (Model Context Protocol) server** (Python / FastMCP) that exposes this repository's **Skills, Agents, and Rules** to any MCP client (Claude Code, Cursor, Codex). Rather than copying assets into each project, a connected agent can **search the catalog and fetch exactly what it needs on demand** -- and ask which conventions apply to a file before editing it. It reads `claude/` as the source of truth and also surfaces the five Render-only skills from `codex/skills/`. Every tool is annotated read-only; the server never writes to your repo.

> **Hosted instance:** LaunchPadLab runs one at `https://ai-bank.launchpadlab.app/mcp` behind
> Cloudflare Access. Browsers sign in with a `@launchpadlab.com` one-time PIN; MCP clients connect
> with a Cloudflare service-token (or `cloudflared`) header — see [`server/README.md`](server/README.md)
> for the exact client config.

#### Install as a Claude Code plugin

The easiest way to connect Claude Code to the hosted server is the **`ai-bank` plugin** in this repo's marketplace -- no manual `.mcp.json` editing:

```bash
/plugin marketplace add LaunchPadLab/ai-bank
/plugin install ai-bank@launchpadlab
```

On enable, Claude Code prompts for a Cloudflare Access **service token** (Client ID + Secret, from the team secrets manager); the secret is stored in your OS keychain. To auto-enable it for a team, add the marketplace and `enabledPlugins` to a project's `.claude/settings.json` -- see [`plugins/ai-bank/README.md`](plugins/ai-bank/README.md). Non-plugin clients (Cursor, Codex) and local stdio runs still use the manual config below.

**Tools** -- progressive disclosure, so `search`/`list_*` return lightweight summaries and `get_*` return full bodies:

| Tool | Purpose |
|---|---|
| `search(query, kind, limit)` | Ranked keyword search across skills, agents, and rules |
| `catalog_overview()` | Asset counts, whether Render skills are included, and any load warnings |
| `list_skills(source)` / `get_skill(name)` | Skill summaries / full SKILL.md body, references, and the agents that use it |
| `list_skill_references(name)` / `get_skill_reference(name, filename)` | A skill's supporting reference docs |
| `list_agents()` / `get_agent(name)` | Agent summaries / full system prompt with resolved skill links |
| `list_rules(include_general)` / `get_rule(name)` | Rule summaries / full rule body and path globs |
| `get_rules_for_path(path, include_general)` | The convention rules that apply to a repo-relative file path, bodies inline -- call this before editing a file |

**Resources:** JSON catalogs at `aibank://skills`, `aibank://agents`, `aibank://rules`, plus templated `aibank://skill/{name}`, `aibank://agent/{name}`, `aibank://rule/{name}`, and `aibank://skill/{name}/reference/{filename}`.

**Prompts:** the six [`claude/commands`](claude/commands/) slash-commands, exposed as MCP prompts.

**Transports & security:** stdio (default, launched by a local client) or streamable HTTP. HTTP binds `127.0.0.1` by default, accepts an optional static bearer token via `AIBANK_MCP_TOKEN`, and refuses to start on a non-loopback host without one. All logging goes to stderr so the stdio JSON-RPC channel stays clean.

**Run it:**

```bash
cd server
uv venv && uv pip install -e ".[dev]"   # Python >= 3.10
uv run aibank-mcp                        # stdio (default)
uv run aibank-mcp --transport http       # streamable HTTP on :8000
uv run pytest                            # run the test suite
```

**Connect Claude Code** (an absolute path to the venv console script avoids PATH/activation issues):

```bash
claude mcp add ai-bank -- /path/to/ai-bank/server/.venv/bin/aibank-mcp
```

See [`server/README.md`](server/README.md) for the complete tool reference, all environment variables, the security model, and ready-to-paste client configuration for Claude Code, Cursor, and Codex.

---

### Codex Catalog

The `codex/` directory contains Codex-native versions of the Claude assets in this repository:

| Path | Purpose |
|---|---|
| [`codex/agents/`](codex/agents/) | Custom Codex subagents as TOML files. These are transposed from `claude/agents/*.md`. |
| [`codex/skills/`](codex/skills/) | Codex skill packages with `SKILL.md`, references, scripts, templates, and assets. |
| [`codex/rules/`](codex/rules/) | Directory-scoped `AGENTS.md` templates transposed from Claude `paths:` rules. |
| [`codex/scripts/`](codex/scripts/) | Scripts for regenerating, validating, and auditing the transposed catalog. |

Codex does not use Claude's `.claude/rules/*.md` `paths:` frontmatter. Instead, Codex loads `AGENTS.md` by directory scope: a root `AGENTS.md` applies broadly, while a nested file such as `app/models/AGENTS.md` applies to that directory and below. The templates under `codex/rules/` are meant to be copied into matching paths in a target project.

Codex subagents are TOML files. Use project-scoped agents in `.codex/agents/` when they should belong to one repository, or personal agents in `~/.codex/agents/` when you want them available across projects.

To regenerate the Codex catalog from the Claude source assets:

```bash
python3 codex/scripts/transpose_claude_skills.py
python3 codex/scripts/transpose_claude_agents.py
python3 codex/scripts/transpose_claude_rules.py
```

Validate the generated catalog before copying it into another setup:

```bash
python3 codex/scripts/validate_codex_skills.py codex/skills
python3 codex/scripts/validate_codex_agents.py codex/agents
python3 codex/scripts/validate_codex_rules.py codex/rules
python3 codex/scripts/audit_transposition.py claude codex
```

---

### Claude Skills

Skills live in `claude/skills/` and are organized by domain. To use a skill in a project, copy or symlink the skill directory into your project's `.claude/skills/` directory.

#### Rails Core Patterns

| Skill | Description |
|---|---|
| [`action-cable-patterns`](claude/skills/action-cable-patterns/) | Real-time features with Action Cable and WebSockets |
| [`action-mailer-patterns`](claude/skills/action-mailer-patterns/) | Transactional emails with Action Mailer and TDD |
| [`active-storage-setup`](claude/skills/active-storage-setup/) | File uploads with variants and direct uploads |
| [`api-patterns`](claude/skills/api-patterns/) | REST API patterns with respond_to blocks, Jbuilder, token auth, and pagination |
| [`authentication-flow`](claude/skills/authentication-flow/) | Authentication using the Rails 8 built-in generator |
| [`avo-resources`](claude/skills/avo-resources/) | Avo 3.x admin panel resources, fields, associations, and authorization |
| [`caching-strategies`](claude/skills/caching-strategies/) | Fragment, Russian doll, and low-level caching patterns |
| [`database-migrations`](claude/skills/database-migrations/) | Safe migrations with proper indexes and rollback strategies |
| [`events-patterns`](claude/skills/events-patterns/) | Event tracking, activity feeds, webhook delivery, and audit trails |
| [`form-object-patterns`](claude/skills/form-object-patterns/) | Form objects for multi-model and wizard forms |
| [`i18n-patterns`](claude/skills/i18n-patterns/) | Internationalization with Rails I18n for multi-language support |
| [`multi-tenant-patterns`](claude/skills/multi-tenant-patterns/) | URL-based multi-tenancy, account scoping, and data isolation |
| [`performance-optimization`](claude/skills/performance-optimization/) | N+1 queries, slow queries, and memory problem detection |
| [`policy-patterns`](claude/skills/policy-patterns/) | Pundit authorization policies with TDD for role-based access control |
| [`rails-architecture`](claude/skills/rails-architecture/) | Modern Rails 8 architecture decisions and layered design |
| [`rails-concern`](claude/skills/rails-concern/) | Shared behavior across models and controllers with TDD |
| [`rails-controller`](claude/skills/rails-controller/) | Controllers with TDD -- request spec first, then implementation |
| [`rails-model-generator`](claude/skills/rails-model-generator/) | Models with TDD -- spec first, then migration, then model |
| [`rails-presenter`](claude/skills/rails-presenter/) | Presenter objects for view formatting using SimpleDelegator |
| [`rails-query-object`](claude/skills/rails-query-object/) | Query objects for complex database queries following TDD |
| [`rails-service-object`](claude/skills/rails-service-object/) | Service objects following single-responsibility with specs |
| [`sidekiq-setup`](claude/skills/sidekiq-setup/) | Background jobs with Sidekiq, queues, and Redis configuration |
| [`state-records-patterns`](claude/skills/state-records-patterns/) | "State as records, not booleans" pattern for rich state tracking |
| [`viewcomponent-patterns`](claude/skills/viewcomponent-patterns/) | Reusable UI components with ViewComponent and TDD |

#### Hotwire, Frontend, and Native Mobile

| Skill | Description |
|---|---|
| [`hotwire-native-android`](claude/skills/hotwire-native-android/) | Hybrid Android apps with Hotwire Native and Kotlin |
| [`hotwire-native-auth`](claude/skills/hotwire-native-auth/) | Web-based authentication for Hotwire Native iOS and Android |
| [`hotwire-native-ios`](claude/skills/hotwire-native-ios/) | Hybrid iOS apps with Hotwire Native and Swift/UIKit |
| [`hotwire-native-path-config`](claude/skills/hotwire-native-path-config/) | Path configuration routing and navigation rules |
| [`stimulus-patterns`](claude/skills/stimulus-patterns/) | Stimulus controller patterns, lifecycle, targets, values, and actions |
| [`tailwind-patterns`](claude/skills/tailwind-patterns/) | Tailwind CSS 4 utility patterns, responsive layouts, and accessibility |
| [`turbo-patterns`](claude/skills/turbo-patterns/) | Turbo Streams, Turbo Frames, morphing, and broadcasting patterns |

#### TDD and Code Quality

| Skill | Description |
|---|---|
| [`code-review`](claude/skills/code-review/) | Code quality analysis, architecture audits, and anti-pattern detection |
| [`lint-patterns`](claude/skills/lint-patterns/) | RuboCop rules, ERB lint, auto-correct patterns, and Rails Omakase standards |
| [`red-test-patterns`](claude/skills/red-test-patterns/) | RED phase test templates for writing failing Minitest tests before implementation |
| [`refactoring-patterns`](claude/skills/refactoring-patterns/) | Refactoring recipes, anti-pattern detection, and codebase modernization |
| [`tdd-cycle`](claude/skills/tdd-cycle/) | Red-Green-Refactor TDD workflow guidance |
| [`testing-patterns`](claude/skills/testing-patterns/) | Eight proven refactoring patterns with before/after Ruby examples |

#### Feature Planning and Orchestration

| Skill | Description |
|---|---|
| [`feature-plan`](claude/skills/feature-plan/) | TDD implementation plans with incremental PR breakdown and agent assignments |
| [`feature-review`](claude/skills/feature-review/) | Feature spec review, scoring, gap analysis, and Gherkin scenario generation |
| [`feature-spec`](claude/skills/feature-spec/) | Structured interview for creating complete feature specifications |
| [`implement-patterns`](claude/skills/implement-patterns/) | Feature orchestration recipes, agent coordination, and dependency ordering |

#### Meta

| Skill | Description |
|---|---|
| [`skill-creator`](claude/skills/skill-creator/) | Guide and tooling for creating new skills |

---

### Claude Agents

Agents live in `claude/agents/`. To use an agent in a project, copy or symlink the agent file into your project's `.claude/agents/` directory. Agents can then be invoked by name (e.g., `@test-agent`) in Claude Code.

#### Orchestrators

| Agent | Description |
|---|---|
| [`implement-agent`](claude/agents/implement-agent.md) | Orchestrates all specialized agents to implement complete Rails features |
| [`refactoring-agent`](claude/agents/refactoring-agent.md) | Orchestrates all specialized agents to refactor Rails codebases |

#### Feature Planning Agents

| Agent | Description |
|---|---|
| [`feature-plan-agent`](claude/agents/feature-plan-agent.md) | Creates TDD implementation plans with incremental PR breakdown and agent assignments |
| [`feature-review-agent`](claude/agents/feature-review-agent.md) | Reviews feature specs for completeness, scores quality, and identifies gaps |
| [`feature-spec-agent`](claude/agents/feature-spec-agent.md) | Guides structured interviews to create complete feature specifications with Gherkin scenarios |

#### Rails Feature Agents

| Agent | Description |
|---|---|
| [`api-agent`](claude/agents/api-agent.md) | Builds REST APIs with same controllers, different formats |
| [`auth-agent`](claude/agents/auth-agent.md) | Implements custom passwordless authentication without Devise |
| [`avo-agent`](claude/agents/avo-agent.md) | Creates and configures Avo 3.x resources for admin panels |
| [`caching-agent`](claude/agents/caching-agent.md) | Implements HTTP caching with ETags, fresh_when, and fragment caching |
| [`concerns-agent`](claude/agents/concerns-agent.md) | Creates and refactors model and controller concerns |
| [`crud-agent`](claude/agents/crud-agent.md) | Generates CRUD controllers following the "everything is CRUD" philosophy |
| [`events-agent`](claude/agents/events-agent.md) | Builds event tracking and activity systems with webhooks |
| [`jobs-agent`](claude/agents/jobs-agent.md) | Implements background jobs using Sidekiq for asynchronous processing |
| [`mailer-agent`](claude/agents/mailer-agent.md) | Creates Action Mailer emails with layouts, previews, and delivery patterns |
| [`migration-agent`](claude/agents/migration-agent.md) | Creates migrations with UUIDs, account scoping, and no foreign keys |
| [`model-agent`](claude/agents/model-agent.md) | Builds rich domain models with associations, scopes, and business logic |
| [`multi-tenant-agent`](claude/agents/multi-tenant-agent.md) | Implements URL-based multi-tenancy with account scoping |
| [`policy-agent`](claude/agents/policy-agent.md) | Creates Pundit authorization policies with Minitest tests and scope restrictions |
| [`presenter-agent`](claude/agents/presenter-agent.md) | Creates presentation logic objects (Presenters/Decorators) for views |
| [`query-agent`](claude/agents/query-agent.md) | Creates encapsulated, reusable query objects |
| [`rails-expert`](claude/agents/rails-expert.md) | Expert Rails 8.x generalist with modern conventions and Hotwire |
| [`service-agent`](claude/agents/service-agent.md) | Creates well-structured service objects following SOLID principles |
| [`state-records-agent`](claude/agents/state-records-agent.md) | Implements "state as records, not booleans" pattern |
| [`stimulus-agent`](claude/agents/stimulus-agent.md) | Builds focused, single-purpose Stimulus controllers |
| [`test-agent`](claude/agents/test-agent.md) | Writes Minitest tests, integration tests, and fixtures |
| [`turbo-agent`](claude/agents/turbo-agent.md) | Creates Turbo Streams, Turbo Frames, and morphing patterns |

#### TDD Agents

| Agent | Description |
|---|---|
| [`tdd-red-agent`](claude/agents/tdd-red-agent.md) | Writes focused, failing Minitest tests during the TDD RED phase |
| [`tdd-refactoring-agent`](claude/agents/tdd-refactoring-agent.md) | Improves code structure while keeping tests green during the TDD REFACTOR phase |

#### Frontend and UI Agents

| Agent | Description |
|---|---|
| [`frontend-developer`](claude/agents/frontend-developer.md) | Builds robust, scalable React components and frontend solutions |
| [`tailwind-agent`](claude/agents/tailwind-agent.md) | Tailwind CSS 4 styling for Rails 8.x ERB views and ViewComponents |
| [`ui-designer`](claude/agents/ui-designer.md) | Visual designer specializing in intuitive, accessible interfaces |
| [`view-component-agent`](claude/agents/view-component-agent.md) | Reusable, tested, performant ViewComponents for Rails 8.x |

#### Infrastructure and Quality Agents

| Agent | Description |
|---|---|
| [`compliance-auditor`](claude/agents/compliance-auditor.md) | GDPR, HIPAA, PCI DSS, SOC 2, and ISO compliance validation |
| [`database-optimizer`](claude/agents/database-optimizer.md) | Query optimization, indexes, and database performance tuning |
| [`hotwire-native-android-agent`](claude/agents/hotwire-native-android-agent.md) | Hybrid Android apps with Hotwire Native and Kotlin |
| [`hotwire-native-ios-agent`](claude/agents/hotwire-native-ios-agent.md) | Hybrid iOS apps with Hotwire Native and Swift |
| [`lint-agent`](claude/agents/lint-agent.md) | Auto-corrects Ruby and Rails code style using RuboCop and ERB lint |
| [`performance-monitor`](claude/agents/performance-monitor.md) | System-wide metrics, anomaly detection, and observability |
| [`postgres-pro`](claude/agents/postgres-pro.md) | PostgreSQL administration, internals, and performance |
| [`prompt-engineer`](claude/agents/prompt-engineer.md) | Designs, optimizes, and evaluates prompts for production LLM systems |
| [`review-agent`](claude/agents/review-agent.md) | Code review for adherence to modern Rails patterns and conventions |
| [`security-agent`](claude/agents/security-agent.md) | Rails security auditing, vulnerability detection, and OWASP best practices |

---

### Claude Commands

Commands are slash commands that Claude Code can invoke. They live in `claude/commands/`. To use a command, copy the file into your project's `.claude/commands/` directory. Invoke with `/command-name` in Claude Code.

| Command | Description |
|---|---|
| [`create-prd`](claude/commands/create-prd.md) | Generate a Product Requirements Document from feature and JTBD documentation |
| [`create-pull-request`](claude/commands/create-pull-request.md) | Create a GitHub PR using the CLI with standardized templates |
| [`frame-problem`](claude/commands/frame-problem.md) | Challenge stakeholder requests to identify real needs and propose optimal solutions |
| [`pr-review`](claude/commands/pr-review.md) | Multi-role PR review: Developer, QA, Security, DevOps, and UX perspectives |
| [`refine-specification`](claude/commands/refine-specification.md) | Ask clarifying questions to refine feature specifications with structured answers |
| [`sync-asana`](claude/commands/sync-asana.md) | Sync user stories from markdown to Asana |

---

### Claude Rules

Rules live in `claude/rules/` and use `paths:` in YAML frontmatter for path-based activation in Claude Code. When you are working in files matching a rule's paths, the rule automatically loads into context. To use a rule, copy the file into your project's `.claude/rules/` directory.

| Rule | Paths | Description |
|---|---|---|
| [`android`](claude/rules/android.md) | `android/**/*` | Hotwire Native Android conventions for Kotlin and Gradle |
| [`anti-patterns`](claude/rules/anti-patterns.md) | `app/**/*.rb`, `test/**/*.rb` | Common anti-patterns to avoid in Ruby and Rails code |
| [`avo`](claude/rules/avo.md) | `app/avo/**/*.erb`, `test/avo/**/*.rb` | Avo 3.x resource and view conventions |
| [`avo-controllers`](claude/rules/avo-controllers.md) | `app/controllers/avo/**/*.rb` | Avo controller patterns and overrides |
| [`cli`](claude/rules/cli.md) | -- | Development CLI commands reference (`bin/dev`, `rails test`, etc.) |
| [`controllers`](claude/rules/controllers.md) | `app/controllers/**/*.rb`, `test/controllers/**/*.rb` | Controller conventions, CRUD patterns, and request specs |
| [`frontend`](claude/rules/frontend.md) | `**/*.js`, `**/*.ts`, `app/javascript/` | JavaScript/TypeScript and Stimulus conventions |
| [`git-conventions`](claude/rules/git-conventions.md) | -- | Git commit messages and PR conventions |
| [`ios`](claude/rules/ios.md) | `ios/**/*` | Hotwire Native iOS conventions for Swift and UIKit |
| [`jobs`](claude/rules/jobs.md) | `app/jobs/**/*.rb`, `test/jobs/**/*.rb` | Background job conventions with Sidekiq |
| [`mailers`](claude/rules/mailers.md) | `app/mailers/**/*.rb`, `app/views/**/*_mailer/**/*.erb` | Action Mailer conventions and email templates |
| [`migrations`](claude/rules/migrations.md) | `db/migrate/**/*.rb`, `db/schema.rb` | Migration conventions, UUIDs, and index strategies |
| [`models`](claude/rules/models.md) | `app/models/**/*.rb`, `test/models/**/*.rb` | Model conventions, associations, validations, and scopes |
| [`policies`](claude/rules/policies.md) | `app/policies/**/*.rb`, `test/policies/**/*.rb` | Pundit authorization policy conventions |
| [`principles`](claude/rules/principles.md) | -- | Development principles: KISS, DRY, YAGNI, and conventions |
| [`queries`](claude/rules/queries.md) | `app/queries/**/*.rb`, `test/queries/**/*.rb` | Query object conventions and patterns |
| [`services`](claude/rules/services.md) | `app/services/**/*.rb`, `test/services/**/*.rb` | Service object conventions and SOLID principles |
| [`styles`](claude/rules/styles.md) | `app/assets/stylesheets/**`, `app/views/**/*.erb` | Tailwind CSS 4 styling and component patterns |
| [`testing`](claude/rules/testing.md) | `test/**/*.rb` | Minitest conventions, fixtures, and test organization |
| [`views`](claude/rules/views.md) | `app/views/**/*.erb`, `app/components/**/*.rb` | ERB view conventions, ViewComponents, and Turbo patterns |

---

### Cursor Rules

Rules live in `cursor/rules/`. To use a rule, copy or symlink the rule directory into your project's `.cursor/rules/` directory. Cursor automatically applies rules based on their frontmatter configuration.

| Rule | `alwaysApply` | Description |
|---|---|---|
| [`hipaa-compliance`](cursor/rules/hipaa-compliance/) | No | Core HIPAA compliance rules for healthcare app development |
| [`hipaa-infrastructure`](cursor/rules/hipaa-infrastructure/) | No | HIPAA-compliant infrastructure requirements for Heroku Shield |
| [`hipaa-notifications`](cursor/rules/hipaa-notifications/) | No | HIPAA-compliant notification and messaging rules |
| [`hipaa-security`](cursor/rules/hipaa-security/) | No | HIPAA security safeguards and authentication requirements |
| [`nova`](cursor/rules/nova/) | No | Nova project workflow rules for AI-assisted development |
| [`nova-process`](cursor/rules/nova-process/) | No | Nova process guidance for structured feature delivery |
| [`scope-sentinel`](cursor/rules/scope-sentinel/) | Yes | Contract compliance, risk management, and consultant-first problem solving |

---

### Templates

| Template | Description |
|---|---|
| [`claude-md-templates/CLAUDE-TEMPLATE.md`](claude-md-templates/CLAUDE-TEMPLATE.md) | Starter template for project CLAUDE.md files covering critical rules, project context, development patterns, agent orchestration, memory management, deployment, and security |

---

### Docker

| File | Description |
|---|---|
| [`cursor/docker/Dockerfile`](cursor/docker/Dockerfile) | Production-ready environment for Cursor Cloud Agents: Ruby 3.4.7, Rails 8.1.1, PostgreSQL 18, Redis, Node.js 20, Chromium for system tests, and a non-root agent user |

Use this Dockerfile as the environment definition for Cursor Cloud Agent tasks. It gives the agent the same toolchain as your local development setup, enabling it to run migrations, execute tests, and verify its own work.

---

### Resources and Documentation

| Resource | Description |
|---|---|
| [`resources/documentation/ai_usage.md`](resources/documentation/ai_usage.md) | Data privacy guide for AI coding tools: training policies, privacy modes, compliance certifications, and configuration checklists for Cursor, Claude Code, GitHub Copilot, Windsurf, and others |
| [`resources/mcp/guides/securing_local_MCP_servers_with_docker.md`](resources/mcp/guides/securing_local_MCP_servers_with_docker.md) | Security guide for running MCP servers in Docker: NGinx proxy, NGrok, and Pinggy tunnel approaches with step-by-step setup |

---

## Getting Started

### Using Skills in a Project

```bash
# Copy a single skill
cp -r claude/skills/rails-architecture /path/to/project/.claude/skills/

# Copy multiple skills at once
cp -r claude/skills/tdd-cycle claude/skills/rails-model-generator /path/to/project/.claude/skills/

# Symlink (changes in ai-bank propagate automatically)
ln -s /path/to/ai-bank/claude/skills/policy-patterns /path/to/project/.claude/skills/policy-patterns
```

### Using Agents in a Project

```bash
cp claude/agents/review-agent.md /path/to/project/.claude/agents/
cp claude/agents/test-agent.md /path/to/project/.claude/agents/
```

### Using Commands in a Project

```bash
cp claude/commands/pr-review.md /path/to/project/.claude/commands/
```

### Using Claude Rules in a Project

```bash
# Copy individual rules
cp claude/rules/models.md /path/to/project/.claude/rules/
cp claude/rules/controllers.md /path/to/project/.claude/rules/

# Copy all rules at once
cp claude/rules/*.md /path/to/project/.claude/rules/
```

### Using Codex Files Locally

Use the `codex/` catalog when setting up OpenAI Codex. Agents, skills, and rules install to different places:

```bash
# Project-scoped Codex subagents
mkdir -p /path/to/project/.codex/agents
cp codex/agents/review-agent.toml /path/to/project/.codex/agents/
cp codex/agents/model-agent.toml /path/to/project/.codex/agents/

# Personal Codex subagents available across projects
mkdir -p ~/.codex/agents
cp codex/agents/rails-expert.toml ~/.codex/agents/
```

Install Codex skills by copying the whole skill package, not just `SKILL.md`:

```bash
# Project-local skills, if your Codex setup loads skills from the project
mkdir -p /path/to/project/.codex/skills
cp -r codex/skills/rails-controller /path/to/project/.codex/skills/
cp -r codex/skills/tdd-cycle /path/to/project/.codex/skills/

# Personal skills, if your Codex setup loads skills from ~/.codex/skills
mkdir -p ~/.codex/skills
cp -r codex/skills/rails-architecture ~/.codex/skills/
```

Install Codex rules by copying selected `AGENTS.md` templates into the matching directories of the target project:

```bash
# Root project guidance
cp codex/rules/root/AGENTS.md /path/to/project/AGENTS.md

# Directory-scoped guidance
mkdir -p /path/to/project/app/models
cp codex/rules/app/models/AGENTS.md /path/to/project/app/models/AGENTS.md

mkdir -p /path/to/project/app/controllers
cp codex/rules/app/controllers/AGENTS.md /path/to/project/app/controllers/AGENTS.md

mkdir -p /path/to/project/db/migrate
cp codex/rules/db/migrate/AGENTS.md /path/to/project/db/migrate/AGENTS.md
```

Symlinks work well if you want updates from this repository to propagate into a local Codex setup:

```bash
ln -s /path/to/ai-bank/codex/agents/review-agent.toml /path/to/project/.codex/agents/review-agent.toml
ln -s /path/to/ai-bank/codex/skills/policy-patterns /path/to/project/.codex/skills/policy-patterns
```

### Using Rules in Cursor

```bash
# Copy a rule directory into the project's Cursor rules folder
cp -r cursor/rules/scope-sentinel /path/to/project/.cursor/rules/

# Or symlink
ln -s /path/to/ai-bank/cursor/rules/hipaa-security /path/to/project/.cursor/rules/hipaa-security
```

### Using the Dockerfile with Cursor Cloud Agents

1. Copy `cursor/docker/Dockerfile` to your project root
2. Push to your repository
3. In Cursor Cloud Agents settings, point the environment to your Dockerfile
4. Cloud agents will build and use this environment for all tasks

---

## Contributing

### Adding a New Skill

1. Create a directory under `claude/skills/` with your skill name (kebab-case)
2. Run the skill initializer to scaffold the structure:
   ```bash
   python3 claude/skills/skill-creator/scripts/init_skill.py your-skill-name --path claude/skills/
   ```
3. Edit `SKILL.md` with frontmatter (`name`, `description`) and instructions
4. Add any reference files, scripts, or assets in the appropriate subdirectories
5. Validate and package the skill:
   ```bash
   python3 claude/skills/skill-creator/scripts/quick_validate.py claude/skills/your-skill-name/
   ```
6. See [`claude/skills/skill-creator/SKILL.md`](claude/skills/skill-creator/SKILL.md) for detailed guidance

### Adding a New Agent

1. Create a markdown file under `claude/agents/` (kebab-case, `.md` extension)
2. Add YAML frontmatter with required fields:
   - `name` - must match the file basename
   - `description` - what the agent does and when to use it
   - `model` - usually `inherit`; document intentional outliers such as `prompt-engineer` using `sonnet`
3. Add optional frontmatter only when needed:
   - `skills` - preload canonical skill packages by slug
   - `maxTurns` - cap focused agents with predictable workflows
   - `disallowedTools` and `permissionMode` - enforce read-only or plan-only agents
   - `isolation` - use for worktree-isolated orchestrators
   - `background` and `memory` - use for long-running reviewers/auditors that need project context
   - `color` - only if the active runner supports and uses it
4. Write the agent's system prompt: role, local discovery workflow, project conventions, capabilities, and boundaries
5. Prefer local skills as the source of truth when an agent and skill cover the same domain
6. Avoid references to collaborator agents or runtime tools that do not exist in `claude/agents/` or the active runner

### Adding a New Claude Rule

1. Create a markdown file under `claude/rules/` (kebab-case, `.md` extension)
2. Add YAML frontmatter. Use `paths:` for file-specific rules:
   ```markdown
   ---
   paths:
     - "app/models/**/*.rb"
     - "test/models/**/*.rb"
   ---
   ```
3. Omit `paths` for rules that should always be available:
   ```markdown
   ---
   ---
   ```
4. Write concise, convention-focused instructions in the body
5. Validate rules:
   ```bash
   python3 claude/rules/scripts/validate_rules.py claude/rules
   ```

### Adding a New Cursor Rule

1. Create a directory under `cursor/rules/` with your rule name
2. Create a `RULE.md` file with YAML frontmatter:
   ```markdown
   ---
   description: Brief description for AI matching
   globs: app/models/**/*.rb
   alwaysApply: false
   ---
   ```
3. Write the rule body with behavioral instructions

### Guidelines

- Skills, agents, and rules should be general enough to reuse across projects unless explicitly scoped to a specific project (like `nova`)
- Keep SKILL.md bodies under 500 lines; move detailed content to `references/` files
- Descriptions in frontmatter are the primary mechanism for AI triggering -- make them specific and include use-case examples
- Test skills and agents on real tasks before contributing
