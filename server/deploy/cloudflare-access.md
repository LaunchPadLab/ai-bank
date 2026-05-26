# Self-hosting the ai-bank MCP server behind Cloudflare Access

This guide stands up a single shared HTTPS endpoint (e.g. `https://aibank.launchpadlab.com/mcp`)
that coworkers connect to from Claude Code / Cursor. **Cloudflare Access** enforces auth at the
edge — Google SSO restricted to `@launchpadlab.com` for people, and a **service token** for the
(headless) MCP client. The server runs in a container reachable only through a Cloudflare Tunnel;
it never listens on a public port, and TLS is Cloudflare's responsibility.

```
Coworker's MCP client ──HTTPS──▶ Cloudflare edge (Access: Google SSO / service token)
                                        │  authenticated requests only
                                        ▼
                              cloudflared tunnel ──▶ aibank-mcp:8000  (private compose network)
```

Because the catalog is **read-only, non-sensitive reference content**, this "trust the proxy"
design is appropriate: Access is the auth layer, so the server itself runs without a token. (For
defense-in-depth you can additionally validate the Access JWT in-server — see
[Optional hardening](#optional-hardening-validate-the-access-jwt-in-server).)

## Prerequisites

- A domain managed in Cloudflare (this example uses `launchpadlab.com`).
- **Cloudflare Zero Trust** enabled on your account (free up to 50 users).
- A host to run Docker (a small VPS, internal box, Fly.io machine, etc.). With the published image
  you need only `docker-compose.yml` + a `.env` — no repo clone. (To build from source instead, a
  checkout of this repo.)

## 1. Create the tunnel

1. Zero Trust dashboard → **Networks → Tunnels → Create a tunnel** → type **Cloudflared** → name it `aibank-mcp`.
2. On the "Install connector" screen, copy the **tunnel token** (the long string after `cloudflared ... run`). You'll paste it into `.env`, not run the shown command — our compose file runs `cloudflared` for you.
3. Add a **Public Hostname**:
   - Subdomain `aibank`, Domain `launchpadlab.com` → `aibank.launchpadlab.com`
   - Service: **HTTP** → URL **`aibank-mcp:8000`** (the compose service name; `cloudflared` resolves it on the internal network)

## 2. Add Google as a login method

Zero Trust → **Settings → Authentication → Login methods → Add new → Google** (or Google Workspace),
following Cloudflare's OAuth setup. This lets people sign in with their `@launchpadlab.com` Google account.

## 3. Protect the hostname with an Access application

Zero Trust → **Access → Applications → Add an application → Self-hosted**.

- **Application domain:** `aibank.launchpadlab.com`
- **Identity providers:** enable Google.
- Add two policies:

  | Policy | Action | Include |
  |---|---|---|
  | `launchpadlab-staff` | Allow | **Emails ending in** `@launchpadlab.com` |
  | `mcp-service-token` | **Service Auth** | **Any Access Service Token** (or a specific token) |

  The Allow policy covers humans using a browser-capable client; the Service Auth policy lets the
  headless MCP client through with token headers.

## 4. Create a service token for MCP clients

Zero Trust → **Access → Service Auth → Create Service Token** → name it (e.g. `mcp-client`).
Copy the **Client ID** (looks like `<uuid>.access`) and **Client Secret** (shown once).

> Tip: create **one service token per coworker** (or per team) so you can revoke an individual's
> access by deleting just their token, without rotating everyone's.

## 5. Deploy

CI publishes the image to GHCR (see [Publishing the image](#publishing-the-image)). On the Docker
host you need only `docker-compose.yml` and a `.env` — no repo clone:

```bash
mkdir aibank-mcp && cd aibank-mcp
curl -fsSLO https://raw.githubusercontent.com/LaunchPadLab/ai-bank/main/server/docker-compose.yml
printf 'CLOUDFLARE_TUNNEL_TOKEN=%s\n' '<your-tunnel-token>' > .env
docker login ghcr.io          # only if the package is private (see Publishing)
docker compose pull
docker compose up -d
```

The server runs on the internal network with no published host port, and `cloudflared` registers
the tunnel. Check it:

```bash
docker compose ps
docker compose logs -f cloudflared   # should report the tunnel registered/healthy
```

To **build from source** instead (inside a clone of this repo):

```bash
cd server
cp .env.example .env          # paste the tunnel token
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

## 6. Connect a client

**Claude Code** — add to `.mcp.json` (project or `~/.claude.json`):

```jsonc
{
  "mcpServers": {
    "ai-bank": {
      "type": "http",
      "url": "https://aibank.launchpadlab.com/mcp",
      "headers": {
        "CF-Access-Client-Id": "<client-id>.access",
        "CF-Access-Client-Secret": "<client-secret>"
      }
    }
  }
}
```

Or via the CLI:

```bash
claude mcp add --transport http ai-bank https://aibank.launchpadlab.com/mcp \
  --header "CF-Access-Client-Id: <client-id>.access" \
  --header "CF-Access-Client-Secret: <client-secret>"
```

**Cursor** — `.cursor/mcp.json`, same `url` + `headers` shape.

Distribute the service-token credentials to coworkers through a secrets manager (1Password/Vault),
not chat. A browser-capable MCP client may instead complete the interactive Google login.

> **Codex caveat:** Codex is stdio-first and its remote-HTTP MCP support is version-dependent.
> Codex users may need the local stdio setup (see the main `server/README.md`) instead.

## Operations

- **Revoke a person:** remove them from Google Workspace, or delete their service token in Access → Service Auth.
- **Rotate:** regenerate the tunnel token (update `.env`, `docker compose up -d`) or the service tokens.
- **Update the catalog:** `git pull` on the host, then `docker compose up -d --build` to rebuild with the latest skills/agents/rules. (Or wire this into CI.)
- **Logs:** `docker compose logs -f`. The MCP server logs to stderr; `cloudflared` reports tunnel health.

## Publishing the image

The container image is built and pushed to GHCR by GitHub Actions
(`.github/workflows/mcp-server-image.yml`) on every push to `main`, on `v*` tags, and via the manual
**Run workflow** button (`workflow_dispatch`). Tags include `latest` (from `main`), `sha-<commit>`,
and semver on release tags. The job runs the test suite first, so a broken build is never published.

Image: **`ghcr.io/launchpadlab/aibank-mcp`**.

**Visibility / access:** GHCR packages are private by default. Either:

- make the package public — GitHub → **Packages** → this package → **Package settings** → change
  visibility (reasonable here, since the catalog is non-sensitive reference content); or
- keep it private and have each host authenticate before pulling:
  `docker login ghcr.io -u <github-user>` with a token that has the `read:packages` scope.

The image does not exist until the workflow has run at least once — **merge to `main` (or trigger the
workflow manually) before the `docker compose pull` step above will work.**

## Security notes

- TLS is terminated by Cloudflare; the origin is private (no published port).
- The server runs unprivileged and is **read-only** — it exposes only the catalog, never writes.
- `AIBANK_MCP_ALLOW_INSECURE_HTTP=1` (set in the image) lets the server bind `0.0.0.0` without its
  own token **because Access is the auth layer**. Do not run the container with a published port on
  an untrusted network without that proxy in front.
- Keep the tunnel token and service-token secrets out of git (the `.env` file is gitignored).

## Optional hardening: validate the Access JWT in-server

For defense-in-depth (so the origin rejects any request that didn't pass Access, even if the
network boundary were bypassed), Cloudflare forwards a signed JWT in the `Cf-Access-Jwt-Assertion`
header. You can verify it in-process with FastMCP's `JWTVerifier`:

- **JWKS URL:** `https://<your-team>.cloudflareaccess.com/cdn-cgi/access/certs`
- **Issuer:** `https://<your-team>.cloudflareaccess.com`
- **Audience (`aud`):** the Access application's **Application Audience (AUD) tag**

This requires a small amount of server code (a custom verifier reading `Cf-Access-Jwt-Assertion`
rather than the standard `Authorization` header). It is **not** wired up by default because, for
this read-only catalog behind a private tunnel, trusting the proxy is sufficient. Open an issue /
ask if you want this layer added.
