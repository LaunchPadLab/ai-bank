# ai-bank plugin

A thin Claude Code plugin that connects to the hosted **ai-bank MCP server** — a read-only
catalog of this repository's Rails/Hotwire **skills, agents, and rules**. The plugin bundles
no content of its own; it points Claude Code at `https://ai-bank.launchpadlab.app/mcp` (behind
Cloudflare Access) so an agent can search the catalog and fetch exactly what it needs on demand.

## What you get

Once enabled, the `ai-bank` MCP server exposes read-only tools, including:

- `search(query, kind, limit)` — ranked keyword search across skills, agents, and rules
- `catalog_overview()` — asset counts and load warnings
- `list_skills` / `get_skill`, `list_skill_references` / `get_skill_reference`
- `list_agents` / `get_agent`
- `list_rules` / `get_rule`
- `get_rules_for_path(path)` — the convention rules that apply to a file — call this before editing

## Install

```bash
/plugin marketplace add LaunchPadLab/ai-bank
/plugin install ai-bank@launchpadlab
```

When you enable the plugin, Claude Code prompts for two values from a **Cloudflare Access
service token** (one token per person makes revocation easy — get yours from the team secrets
manager):

- **Cloudflare Access Client ID** — the `CF-Access-Client-Id` value, ending in `.access`
- **Cloudflare Access Client Secret** — the paired `CF-Access-Client-Secret` (stored in your OS keychain)

The client secret is stored securely in your OS keychain, not in `settings.json`.

### Enable for a whole team

Add this to a consuming repository's `.claude/settings.json` so teammates are prompted to
install on folder-trust:

```json
{
  "extraKnownMarketplaces": {
    "launchpadlab": { "source": { "source": "github", "repo": "LaunchPadLab/ai-bank" } }
  },
  "enabledPlugins": { "ai-bank@launchpadlab": true }
}
```

## Verify

In a fresh session, check the server is connected with `/mcp` and confirm the `ai-bank` tools
are available. Try `catalog_overview` or `search` for "controller". A Cloudflare `403` means
the service-token credentials are missing or invalid.

## Alternatives (not provided by this plugin)

This plugin only configures the **hosted** connection over HTTP. For a local stdio server, a
`cloudflared` short-lived token, or manual client configuration (Cursor, Codex), see
[`server/README.md`](../../server/README.md).
