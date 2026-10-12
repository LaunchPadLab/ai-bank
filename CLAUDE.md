# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

AI-BANK is a catalog of reusable AI-tooling assets (skills, agents, rules, commands, templates) for Rails/Hotwire projects, targeting Claude Code, Codex, and Cursor. It also ships a Python backend in `server/` that serves the catalog. Most of the repo is Markdown content, not code.

The assets under `claude/rules/`, `claude/agents/`, etc. are **templates meant for other (Rails) projects**. They are not conventions for working in this repo. For example, `claude/rules/models.md` describes Rails models and does not apply here.

## Content layout and source of truth

- `claude/` is the **canonical source**: `skills/<name>/SKILL.md` (+ `reference/` or `references/`), `agents/*.md`, `rules/*.md` (optional `paths:` glob frontmatter), and `commands/*.md`.
- `codex/` is **generated** from `claude/` by the transposition scripts. Edit the Claude asset and regenerate; don't hand-edit the Codex copy. The one exception is the five vendored Render-only skills (`render-debug`, `render-deploy`, `render-migrate-from-heroku`, `render-monitor`, `render-workflows`), which exist only in `codex/skills/`. The transposition, audit, and validation scripts skip them through `CODEX_ONLY_SKILL_NAMES` in `codex/scripts/codex_transpose.py`, which must stay in sync with `RENDER_ONLY_SKILL_NAMES` in `server/src/aibank_mcp/loader.py`. The canonical `render-operations` skill lives in `claude/` like any other skill.
- `cursor/rules/<name>/RULE.md` uses Cursor frontmatter (`description`, `globs`, `alwaysApply`). Never put `alwaysApply` in Claude rules.
- `plugins/ai-bank/` + `.claude-plugin/marketplace.json` is a Claude Code plugin that only connects to the hosted MCP server.

Asset conventions:
- Agent frontmatter `name` must match the file basename. `skills:` lists canonical skill slugs.
- Keep SKILL.md bodies under 500 lines and move the detail into `references/`.
- Frontmatter `description` is what triggers the asset, so keep it specific.

## Commands

Server (run from `server/`, Python >= 3.10, uses `uv`):

```bash
uv venv && uv pip install -e ".[dev,web]"   # [web] adds FastAPI + anthropic for the chat app
uv run pytest                               # full suite (CI runs: ruff check . && pytest -q)
uv run pytest tests/test_search.py::test_name   # single test
ruff check .
uv run aibank-mcp                           # MCP server, stdio (blocks waiting on stdin — expected)
uv run aibank-mcp --transport http          # streamable HTTP on 127.0.0.1:8000/mcp
uv run aibank-web                           # chat app on 127.0.0.1:8001 (needs ANTHROPIC_API_KEY)
npx @modelcontextprotocol/inspector uv run aibank-mcp   # exercise the MCP server by hand
```

Content validation and generation (run from the repo root):

```bash
python3 claude/rules/scripts/validate_rules.py claude/rules
python3 claude/skills/skill-creator/scripts/quick_validate.py claude/skills/<name>/
python3 claude/skills/skill-creator/scripts/init_skill.py <name> --path claude/skills/

# Regenerate codex/ from claude/ (skills before agents: agents reference codex/skills)
python3 codex/scripts/transpose_claude_skills.py
python3 codex/scripts/transpose_claude_agents.py
python3 codex/scripts/transpose_claude_rules.py
# Validate
python3 codex/scripts/validate_codex_skills.py codex/skills
python3 codex/scripts/validate_codex_agents.py codex/agents
python3 codex/scripts/validate_codex_rules.py codex/rules
python3 codex/scripts/audit_transposition.py claude codex

claude plugin validate . --strict && claude plugin validate ./plugins/ai-bank --strict
```

Docker builds must use the **repo root** as the build context because the image bundles `claude/` and `codex/`: `docker build -f server/Dockerfile -t aibank-mcp .`

## Server architecture (`server/src/`)

There are two packages that share one in-memory catalog:

- **`aibank_mcp`**, the read-only FastMCP server.
  - Content layer: `frontmatter` → `loader` → `models` → `catalog` → `search`. It is pure Python with no FastMCP imports, and it is unit-tested in isolation.
    - `loader` scans `claude/` (and Render skills from `codex/skills/`) into frozen dataclasses. A malformed file becomes a `LoadWarning` instead of a crash.
    - `catalog.build_catalog(repo_root)` produces an immutable snapshot.
  - MCP layer: `tools`, `resources`, `prompts`, `server`, and `cli` are the only FastMCP-aware modules.
    - Every tool is read-only.
    - `get_rules_for_path` matches a file path against the rules' `paths:` globs.
    - `claude/commands/*.md` are exposed as MCP prompts.
- **`aibank_web`**, a FastAPI chat app. It imports `aibank_mcp.catalog` directly, so there is no duplicated retrieval logic.
  - `agent.py` is a hand-written streaming tool-use loop over the Anthropic API. It deliberately avoids the SDK tool runner because it needs per-token SSE and live tool-activity events. Citations are synthesized server-side from the tools that actually ran.
  - `tools.py` defines a static `ANTHROPIC_TOOLS` list (a curated 7-tool subset of the MCP surface). The system prompt is built once at startup. Both must stay **byte-stable** across requests or the prompt cache invalidates, so never build them per request.
  - The frontend in `web/static/` is plain HTML/JS with no build step.

Configuration:
- Repo root comes from `--repo-root` / `AIBANK_REPO_ROOT`. Without either, the server walks up from the package and the CWD to the first directory containing both `claude/skills` and `claude/rules`.
- The MCP server uses `AIBANK_MCP_*` env vars. The chat app uses `AIBANK_WEB_*` env vars (model, effort, and so on) plus `ANTHROPIC_API_KEY`.
- HTTP mode refuses to bind a non-loopback host unless `AIBANK_MCP_TOKEN` or `--allow-insecure-http` is set. All logging goes to stderr so stdio JSON-RPC stays clean.

`server/src/aibank_mcp/frontmatter.py` is vendored from `codex/scripts/codex_transpose.py`, so keep the two in sync. `tests/test_frontmatter.py` locks the behavior.

## Versioning

release-please manages a single unified version. It bumps `server/pyproject.toml`, both `server/src/*/__init__.py`, and `plugins/ai-bank/.claude-plugin/plugin.json` (lines marked `x-release-please-version`), and regenerates `CHANGELOG.md`. Don't bump versions by hand. Write commit and PR titles as Conventional Commits (`feat:`, `fix:`, `feat!:`) because they drive the version bump and the changelog.
