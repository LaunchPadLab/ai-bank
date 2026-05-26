# aibank-mcp

A read-only **MCP (Model Context Protocol) server** that exposes the [ai-bank](../README.md)
knowledge base — **Skills**, **Agents**, and **Rules** — so MCP clients (Claude Code, Cursor,
Codex) can *discover and fetch* assets on demand instead of copying files between projects.

It reads from `claude/` (the canonical source of truth) and additionally surfaces the 5
Render-only skills from `codex/skills/`. Nothing is written: every tool is `readOnlyHint=true`.

## What it exposes

**Tools** (progressive disclosure — `search`/`list_*` are cheap; `get_*` return full bodies):

| Tool | Purpose |
|---|---|
| `search(query, kind="all"\|"skill"\|"agent"\|"rule", limit=15)` | Ranked keyword search across the catalog. |
| `catalog_overview()` | Asset counts, whether Render skills are included, load warnings. |
| `list_skills(source="all"\|"claude"\|"codex")` | Skill summaries + reference filenames. |
| `get_skill(name)` | Full SKILL.md body + metadata + references + which agents use it. |
| `list_skill_references(name)` / `get_skill_reference(name, filename)` | A skill's supporting docs. |
| `list_agents()` / `get_agent(name)` | Agent summaries / full system prompt + resolved skill links. |
| `list_rules(include_general=True)` / `get_rule(name)` | Coding-convention rules. |
| **`get_rules_for_path(path, include_general=True)`** | The rules that apply to a repo-relative file path, bodies inline. Call before editing a file. |

**Resources** (a URI mirror for clients that support them):
`aibank://skills`, `aibank://agents`, `aibank://rules`,
`aibank://skill/{name}`, `aibank://agent/{name}`, `aibank://rule/{name}`,
`aibank://skill/{name}/reference/{filename*}`.

**Prompts**: the `claude/commands/*.md` slash-commands (returned as text, never executed).

## Install & run

Requires Python ≥ 3.10. Uses [FastMCP](https://github.com/jlowin/fastmcp) 3.x.

```bash
cd server
uv venv && uv pip install -e ".[dev]"   # or: pip install -e ".[dev]"

# stdio (default) — what local clients launch. Run it through the venv:
uv run aibank-mcp           # easiest; uses ./.venv
.venv/bin/aibank-mcp        # equivalent, without uv
# (NOT bare `python -m aibank_mcp` — `python` may not exist and won't see the venv.
#  Activate first with `source .venv/bin/activate` if you want the bare command.)

# streamable HTTP:
uv run aibank-mcp --transport http --port 8000
```

> In stdio mode the process logs to stderr and then **waits for a client on stdin** — that's
> expected, not a hang. It is meant to be launched by an MCP client. To exercise it by hand, use
> the inspector (`npx @modelcontextprotocol/inspector uv run aibank-mcp`) or HTTP mode.

Run without a local checkout once published (content is found via `AIBANK_REPO_ROOT`):

```bash
uvx --from "git+https://github.com/<org>/ai-bank.git#subdirectory=server" aibank-mcp
```

## Configuration

| Flag | Env | Default | Notes |
|---|---|---|---|
| `--transport {stdio,http}` | `AIBANK_MCP_TRANSPORT` | `stdio` | stdio for local clients; http for hosted/team use. |
| `--host` | `AIBANK_MCP_HOST` | `127.0.0.1` | HTTP bind host. |
| `--port` | `AIBANK_MCP_PORT` | `8000` | HTTP bind port. |
| `--path` | `AIBANK_MCP_PATH` | `/mcp` | HTTP endpoint path. |
| `--repo-root` | `AIBANK_REPO_ROOT` | auto-detect | Path to the ai-bank checkout. |
| `--log-level` | `AIBANK_MCP_LOG_LEVEL` | `INFO` | Logs go to **stderr** only. |
| `--no-render-skills` | `AIBANK_INCLUDE_RENDER=0` | included | Exclude the codex-only Render skills. |
| `--allow-insecure-http` | `AIBANK_MCP_ALLOW_INSECURE_HTTP=1` | off | Permit a non-loopback bind without a token. Use ONLY behind an authenticating proxy or on a trusted private network. |
| _(env only)_ | `AIBANK_MCP_TOKEN` | _unset_ | Static bearer token required for HTTP auth. |

**Repo-root resolution**: `--repo-root`/`AIBANK_REPO_ROOT` → else auto-detect by walking up from
the package and the CWD for a directory containing both `claude/skills` and `claude/rules`.

## Security

- **stdio** runs as a local child process and needs no auth.
- **HTTP** binds `127.0.0.1` by default. Set `AIBANK_MCP_TOKEN` to require an
  `Authorization: Bearer <token>` header. As a fail-safe, the server **refuses to start** on a
  non-loopback host (e.g. `0.0.0.0`) unless a token is set or `--allow-insecure-http` /
  `AIBANK_MCP_ALLOW_INSECURE_HTTP=1` is given — the explicit opt-out for running behind an
  authenticating proxy (see [Self-hosting](#self-hosting-remote-team-access)).
- The static-token verifier stores the token in plaintext and is meant for simple
  team/internal use. For production, front the server with a TLS-terminating, authenticating
  reverse proxy (nginx/Caddy/Cloudflare Access) and bind to loopback. OAuth, rate limiting, and
  CORS are out of scope. See [`../resources/mcp/guides/securing_local_MCP_servers_with_docker.md`](../resources/mcp/guides/securing_local_MCP_servers_with_docker.md).

## Client configuration

**Claude Code** — `.mcp.json` (committed at a repo root) or `claude mcp add`:

```jsonc
// stdio — point at the venv's console script by ABSOLUTE path (no PATH/activation needed).
// The server auto-detects the ai-bank checkout it lives inside.
{ "mcpServers": { "ai-bank": { "command": "/ABS/PATH/TO/ai-bank/server/.venv/bin/aibank-mcp" } } }
// Alternative via uv: "command": "uv", "args": ["run", "--directory", "/ABS/PATH/TO/ai-bank/server", "aibank-mcp"]
```
```jsonc
// streamable HTTP
{ "mcpServers": { "ai-bank": {
  "type": "http",
  "url": "http://127.0.0.1:8000/mcp",
  "headers": { "Authorization": "Bearer ${AIBANK_MCP_TOKEN}" }
} } }
```
```bash
claude mcp add ai-bank -- /ABS/PATH/TO/ai-bank/server/.venv/bin/aibank-mcp
claude mcp add --transport http ai-bank http://127.0.0.1:8000/mcp
```

**Cursor** — `.cursor/mcp.json` (same schema): `command`/`args` for stdio, `url` for HTTP.

**Codex** — `~/.codex/config.toml` (stdio-first):

```toml
[mcp_servers.ai-bank]
command = "/ABS/PATH/TO/ai-bank/server/.venv/bin/aibank-mcp"
# env = { AIBANK_REPO_ROOT = "/path/to/ai-bank" }  # only needed if run from outside the checkout
```

> Cursor/Codex config shapes evolve — re-check against your installed versions.

## Self-hosting (remote team access)

To give coworkers one shared endpoint, run the server in Docker behind **Cloudflare Access**
(Google SSO restricted to your domain, plus a service token for the headless MCP client). The image
is published to GHCR (`ghcr.io/launchpadlab/aibank-mcp`) by CI, so a host needs only
[`docker-compose.yml`](docker-compose.yml) and a `.env` — no clone. The server binds the internal
container network only and is reachable solely through the `cloudflared` tunnel, so Cloudflare
Access is the auth layer and TLS is handled at the edge.

```bash
# on the Docker host (just the compose file + a tunnel token):
cp .env.example .env          # paste your Cloudflare tunnel token
docker login ghcr.io          # only if the GHCR package is private
docker compose pull && docker compose up -d
```

Full walkthrough — publishing, tunnel, Access application + Google IdP, the `@your-domain.com`
policy, the service token, and client headers — is in
[`deploy/cloudflare-access.md`](deploy/cloudflare-access.md). It also weighs the alternatives
(local-only stdio, Tailscale, a single shared token); a [`Dockerfile`](Dockerfile) +
[`docker-compose.build.yml`](docker-compose.build.yml) support building from source.

## Development

```bash
cd server
uv run pytest          # or: .venv/bin/python -m pytest
ruff check .
```

The content layer (`frontmatter`, `models`, `loader`, `catalog`, `search`) is pure Python and
unit-tested with zero MCP involvement; `tools`/`resources`/`prompts`/`server`/`cli` are the only
FastMCP-aware modules. `tests/` covers the parser, loader, catalog, search, path-glob matching,
and an in-memory MCP integration suite (`fastmcp.Client(build_server(...))`).

The frontmatter parser is vendored from `codex/scripts/codex_transpose.py`; keep the two in sync
(behavior is locked by `tests/test_frontmatter.py`).
