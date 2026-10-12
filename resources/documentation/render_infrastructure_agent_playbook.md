# Render Infrastructure-Agent Playbook — Running Claude Code Agents Against Render Safely

*Internal policy for using Claude Code (the `render-operations` skill, `render-ops-agent`, the Render CLI, the Render MCP server, and `render_remediate.py`) on Render services. Current as of October 2026, Render CLI v2.22–v2.28. Render's plans and roles change, so reverify against [render.com/docs](https://render.com/docs) and [render.com/pricing](https://render.com/pricing).*

## TL;DR

- **Agents get their own Render identity.** Use a dedicated "agent" Render user with the least-privileged role that works. Never use a person's key, and never use an Admin.
- **Read-only by default.** Diagnosis is free. Every change to Render needs a human to approve that specific action.
- **Remediation goes through the script.** Known fixes (OOM crash loop, bad live deploy) run only as `render_remediate.py plan`, then human review, then `apply`. Never improvise API calls.
- **Enforce, don't just instruct.** Render roles, protected environments, and Claude Code `deny`/`ask` rules are hard limits. Prompts and skills are soft limits.
- **Every production change leaves a trail.** Keep the Render audit log, the deploy history, `audit.jsonl`, the plan, the session transcript, and an incident note.

## 1. Setup

| Step | Do this |
|---|---|
| Render CLI | `brew install render`, then `render --version`. Humans authenticate with `render login`, a browser flow that stores a token in `~/.render/cli.yaml` and refreshes it automatically. |
| Agent credential | A Render workspace Admin creates the dedicated agent user and adds it to **only** the target workspace (section 2). Sign in as that user, create an API key under Account Settings → API Keys, and expose it as `RENDER_API_KEY` from the OS keychain or a secret manager. Never put it in a repo, `.env`, or a prompt. |
| Workspace | Run `render workspace current` before any work. Pin it with `render workspace set <id>` or `RENDER_WORKSPACE=<id>`. |
| ai-bank assets | Copy or symlink `claude/skills/render-operations/` and `claude/agents/render-ops-agent.md` into the project's `.claude/`, or fetch them through the ai-bank MCP plugin. |
| Render MCP (optional) | Prefer `/plugin install render@claude-plugins-official`, which uses OAuth. Avoid `claude mcp add ... --header "Authorization: Bearer <key>"`, because it leaves the key in plaintext config. |
| Guardrails | Commit the permissions block from section 2 to the project's `.claude/settings.json`. |

**Why a dedicated user:** a Render API key reaches **every workspace its user belongs to**. It has no scopes and never expires. A dedicated user limits where a key works, makes the user's actions easy to pick out in audit logs, and can be removed without disrupting anyone. Rotate its key quarterly and whenever someone with access leaves.

## 2. Permissions

### Render roles for the agent user

| Role | Availability | What the agent can do | Use for agents? |
|---|---|---|---|
| Viewer | Scale+ | Read-only, and **cannot read logs** | No. Too little for diagnosis. |
| Contributor | Scale+ | View logs, deploy, roll back. Cannot see env vars, use the shell, or create or delete resources. | **Yes, for diagnosis on Scale+.** Covers Green tasks except env-key audits and `render_remediate.py` (both need env-var access). |
| Developer | All team plans | Everything above, plus env vars and the shell in **unprotected** environments | **Yes on Pro, or when running the remediation script.** Pair it with a protected production environment. |
| Admin | All team plans | Everything, including protected environments, members, and billing | **Never** |

**Role and the remediation script:** `render_remediate.py` reads `WEB_CONCURRENCY` on every `plan` and `apply`, including rollback-only plans. A non-404 error at that read exits 1. If Render answers a Contributor with 404 instead, the script treats the key as unset and continues (unverified). Run the script as Developer in an unprotected environment, or have a human Admin run it for protected production.

**Protect production** (Pro+). Set `permissions: protection: enabled` on the environment in `render.yaml`, or toggle it in the dashboard. In a protected environment only Admins can create or delete resources, suspend services, toggle maintenance mode, open a shell, or view or change env vars and secret files. Non-Admins can still change resources by pushing a Blueprint update, so review production `render.yaml` changes in PRs.

### Claude Code permissions

Commit this as the project's `.claude/settings.json`. Rules are evaluated deny → ask → allow, and the first match wins:

```json
{
  "permissions": {
    "allow": [
      "Bash(render services:*)",
      "Bash(render deploys list:*)",
      "Bash(render logs:*)",
      "Bash(render workspace current:*)",
      "Bash(render blueprints validate:*)",
      "Bash(python3 *render_remediate.py plan*)",
      "Bash(jq:*)"
    ],
    "ask": [
      "Bash(render deploys create:*)",
      "Bash(render deploys cancel:*)",
      "Bash(render restart:*)",
      "Bash(render services update:*)",
      "Bash(render services create:*)",
      "Bash(python3 *render_remediate.py apply*)",
      "mcp__render__trigger_deploy",
      "mcp__render__update_environment_variables",
      "mcp__render__create_*"
    ],
    "deny": [
      "Bash(render ssh:*)",
      "Bash(render services delete:*)",
      "Bash(curl *-X DELETE*)",
      "Bash(curl *--request DELETE*)",
      "Read(~/.render/**)",
      "Read(**/.env*)"
    ]
  }
}
```

- `render services:*` also matches `create` and `delete`. The `ask` and `deny` entries for those take precedence over the allow.
- Replace `mcp__render__` with your actual tool prefix: `mcp__plugin_render_<server>__` after a plugin install, or `mcp__claude_ai_Render__` for the claude.ai connector.
- Bash rules match command text, so they stop mistakes but not a determined bypass such as `sh -c`. When a limit must hold, put the `deny` rules in **managed settings** (`/Library/Application Support/ClaudeCode/managed-settings.json` on macOS) and use the sandbox network allowlist.
- Settings layering and hooks: [customizing_claude_code_system_prompt.md](customizing_claude_code_system_prompt.md) §4–6.

## 3. Safety Controls

Defense in depth. Each layer assumes the one below it can fail.

| Layer | Control | Strength |
|---|---|---|
| Render | Agent user's role, protected production environment | Hard (platform) |
| Claude Code | `deny`/`ask` rules, managed settings, optional PreToolUse hook | Hard (harness) |
| Remediation script | 30-minute plan expiry, `--confirm <service-id>`, 4-action allowlist, state fingerprint, no deploy in progress. Stops and prints revert steps after a failed request (exit 1) or failed verification (exit 4). | Hard (code) |
| `render-ops-agent` | Boundaries: Always / Ask first / Never | Soft (prompt) |
| `render-operations` skill | Safety Rules: read-only default, state the workspace and service ID, mask secrets | Soft (prompt) |

**Never:**
- Delete services or datastores.
- Replace the whole env-var collection with `PUT /env-vars` without first showing the full key diff. It deletes every key it omits.
- Print secret values into chat or logs.
- Pass `--confirm` before the user has approved.
- Hand-edit `plan.json`.

**Watch out:** the Render MCP `update_environment_variables` tool **deploys immediately**. REST env-var updates **never** deploy, and `render restart` does not pick up new values. Make sure everyone knows which path is in use before changing env vars.

## 4. Escalation Rules

| Trigger | Agent does | Escalate to |
|---|---|---|
| Build or pre-deploy failed and the old deploy is still serving | Diagnose and propose a fix forward | No one (normal PR flow) |
| `plan` exits 2 with automatic actions | Show `plan.md`, get approval, `--dry-run`, then `apply` | The approving engineer |
| `plan` exits 2 with only manual steps, or `apply` exits 3 (refused, nothing sent) | Follow the manual steps, or re-run `plan`. Never edit `plan.json`. | The approving engineer |
| `apply` exits 4, or exits 1 partway | Stop. Report the completed steps and the printed revert steps. | **On-call engineer** |
| Second failed remediation on the same service, or production down for more than 15 minutes | Stop all changes | **On-call, then tech lead** |
| Rollback would cross a migration, or any change in a protected environment, secret, or env group | Plan only | **Tech lead** (human executes) |
| status.render.com incident, eviction, or `server_hardware_failure` events | Read-only monitoring | **Render support** (dashboard ticket or support@render.com). Premium support and SLAs are an add-on on Pro and Scale and included on Enterprise. |
| A secret appears in a transcript, log, or plan, or a key may be exposed | Stop. Do not repeat the value. | **Security**: revoke the key in Account Settings immediately, then rotate |

**Paging:** send Render failure notifications (email or Slack) to the team's ops channel. On Pro+, an Admin can add a webhook (`server_failed`, `deploy_ended`) to feed paging, verifying the Standard Webhooks HMAC signature.

## 5. Auditability

| Record | Where | Covers | Retention |
|---|---|---|---|
| Render workspace audit log (Pro+) | Workspace Settings → Compliance, CSV export (Admins), or `GET /v1/owners/{ownerId}/audit-logs` | Env var create, update, delete, and **value views**. Shell sessions. Member and role changes. Auto-deploy changes. **Not deploys.** | At least 90 days |
| Deploy history | `render deploys list <srv> -o json` | Every deploy, its trigger (`rollback`, `api`, `new_commit`, and so on) and commit | Per Render |
| Remediation audit | `~/.render-remediation/audit.jsonl` (mode 600) | One line per request (`at`, `service`, `detector`, `action`, `request`, `status`, `deployId` or `error`), plus the `verify` result | Local. Attach it to the incident. |
| Approval artifact | `~/.render-remediation/plans/<srv>-<stamp>/plan.md` | Evidence, the exact API calls, risks, and revert steps the human approved | Local. Link it in the incident. |
| Agent session | Claude Code transcript | What the agent ran and why | Export it for incidents |
| Incident note | Template in [failed-deploy-recovery.md](../../claude/skills/render-operations/references/failed-deploy-recovery.md) | Timeline, impact, root cause, fix, follow-ups | Team docs |

**Rule:** any agent-driven change to production needs an incident note that links the plan or transcript and the deploy IDs.

## 6. Recommended Use Cases

| Tier | Agent may | Examples |
|---|---|---|
| **Green**: agent runs it unprompted (read-only) | Diagnose and report | Deploy status and "what's live"; build-failure triage; log and request-ID searches; OOM and crash-loop diagnosis; env **key** audits and `render.yaml` drift checks; `render_remediate.py plan` |
| **Yellow**: agent proposes, a human approves each action | Execute after approval | Guarded `apply` (step `WEB_CONCURRENCY` down, roll back a bad deploy); redeploy a known-good commit; cancel a stuck deploy; restart; a single non-secret env var change in an unprotected environment |
| **Red**: humans only | Plan or advise at most | Deleting anything; secrets and protected environments; plan, scaling, and billing changes; database restores and destructive migrations; domains and DNS; creating or rotating API keys; production Blueprint changes |

## Recommendations

- **Stage 1, read-only in staging.** Give the agent user Contributor (Scale+, diagnosis only) or Developer in a staging workspace or environment. Run Green tasks only for two weeks and review the transcripts.
- **Stage 2, guarded remediation in staging.** Allow Yellow tasks with the `ask` rules. Rehearse `plan` → `apply` → exit 4 → revert at least once.
- **Stage 3, production.** Protect the production environment, put the `deny` rules in managed settings, wire up failure notifications, and keep Yellow actions behind per-action approval.
- **Change the plan if:**
  - an agent action ever lands in the wrong workspace: move to a per-workspace agent user;
  - Yellow approvals become rubber-stamps: shrink the Yellow list.

## Caveats

- Render's docs don't say whether an API key is limited to its user's role. The rest of this playbook assumes it is. Confirm with Render support before relying on role limits for a key.
- How API-key actions are attributed in the audit log isn't documented. Deploys aren't audit-logged at all.
- Sources disagree on whether SAML SSO and SCIM need Scale or Enterprise.
- The Render MCP server has mutating tools and, per Render, does not guarantee secrets stay out of the model's context. Use it only with the `ask` rules above.
- Recheck `render <cmd> --help` after CLI upgrades.
