---
name: "render-operations"
description: "Day-2 operations runbooks for services already running on Render, driven by the Render CLI with Render MCP and REST API fallbacks. Use when checking Render deployment status, investigating a build_failed, pre_deploy_failed, or update_failed deployment, reading Render app, request, or build logs, inspecting OOM kills or restarts, managing Render environment variables, env groups, or secret files, or running a rollback and recovering from a failed Render deployment. For first-time setup and render.yaml generation use render-deploy; for Heroku moves use render-migrate-from-heroku."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools, argument-hint. -->

# Render Operations

**Target service: $ARGUMENTS**

## Overview

Four documented workflows for operating an app that is already on Render. Each one is a step-by-step runbook with exact commands, a symptom → cause → fix table, Rails notes, and a "done when" check.

| Situation | Workflow |
|---|---|
| "Did it deploy?", "why did the build fail?", a deploy stuck in progress | [Deployment status and build failures](references/deploy-status-and-build-failures.md) |
| Errors in production, 5xx spikes, slow requests, OOM, restarts, cron or datastore logs | [Application and infrastructure logs](references/logs.md) |
| Add, change, audit, or rotate env vars, env groups, secret files, Blueprint `envVars` | [Environment configuration](references/environment-configuration.md) |
| Production is broken after a release, or a deploy failed and needs a way back | [Failed deployment recovery](references/failed-deploy-recovery.md) |

Start with the workflow that matches the symptom. They link to each other where one hands off to another, for example a build failure caused by a missing env var.

## Prerequisites

```bash
render --version                 # Render CLI; brew install render (or see render.com/docs/cli)
render login                     # interactive; or export RENDER_API_KEY=rnd_... for scripts/CI
render workspace current         # confirm the workspace before doing anything
render workspace set <name-or-id>
```

Non-interactive conventions, used in every workflow:

- Pass `-o json` when you will parse output and `-o text` when you only read it. The CLI switches to text automatically when stdout is not a TTY, and `CI=1` forces that.
- `--confirm` skips prompts. **Only add it after the user has approved the action.**
- Most commands take a service ID (`srv-...`). Resolve names to IDs once with `render services -o json` and reuse the ID.

## Tooling Matrix

The CLI does not cover everything. When it cannot do a step, the workflow names the Render MCP tool and the REST endpoint (base `https://api.render.com/v1`, header `Authorization: Bearer $RENDER_API_KEY`).

| Capability | Render CLI | Render MCP | REST API |
|---|---|---|---|
| List services / instances | `render services`, `render services instances <srv>` | `list_services`, `get_service` | `GET /services` |
| List / inspect deploys | `render deploys list <srv>` | `list_deploys`, `get_deploy` | `GET /services/{id}/deploys[/{deployId}]` |
| Trigger deploy (commit, image, clear cache) | `render deploys create <srv> [--commit] [--image] [--clear-cache] [--wait]` | `trigger_deploy` | `POST /services/{id}/deploys` |
| Cancel deploy | `render deploys cancel <srv> <deploy>` | — | `POST /services/{id}/deploys/{deployId}/cancel` |
| Roll back | — (dashboard) | — | `POST /services/{id}/rollback` |
| Restart | `render restart <srv>` | — | `POST /services/{id}/restart` |
| Logs (app, request, build) | `render logs -r <ids> ...` | `list_logs`, `list_log_label_values` | `GET /logs` |
| Events (failures, restarts, autoscaling) | — | `list_events` | `GET /services/{id}/events` |
| Metrics (CPU, memory, HTTP) | — | `get_metrics` | `GET /metrics/*` |
| Env vars / secret files | — (only at `services create`) | `update_environment_variables` | `GET/PUT /services/{id}/env-vars[/{key}]` |
| Env groups | — | — | `/env-groups/...` |
| Health check, auto-deploy, maintenance mode | `render services update <srv> ...` | — | `PATCH /services/{id}` |
| Validate Blueprint | `render blueprints validate [render.yaml]` | — | — |
| Shell / psql | `render ssh <srv>`, `render psql <db>` | `query_render_postgres` (read-only) | — |

Verified against Render CLI v2.22 through v2.28, where none of the gaps marked "—" have a CLI command. Re-check with `render <command> --help` on newer versions.

**The env var paths behave differently:**
- The MCP tool `update_environment_variables` merges by default (`replace: true` replaces everything) and **triggers a deploy automatically**.
- The REST `PUT` endpoints **do not deploy**. The change takes effect on the next deploy.

## Safety Rules

Read-only by default. **Stop and get explicit user approval before any of these:**

- Triggering, cancelling, or rolling back a deploy, or restarting a service.
- Creating, changing, or deleting env vars, env groups, or secret files.
- Changing auto-deploy, the health check path, or maintenance mode.

Also:

- Never print secret values. Show env var **keys**, and mask values as `abc…xyz` when you must compare them.
- Never `PUT /services/{id}/env-vars` (the collection) without first showing the user the full diff. It **replaces every var**, and any key you omit is deleted.
- Never delete services or datastores from this workflow.
- State the workspace and service ID in every proposal for a mutating action, so the user can catch a wrong target.

## Rails on Render: Quick Checklist

Most Rails incidents on Render come from one of these:

- **Build:** `bin/render-build.sh` is executable (`chmod a+x`) and runs `bundle install`, `bin/rails assets:precompile`, and `bin/rails assets:clean`.
- **Migrations:** on paid plans, set `preDeployCommand: bundle exec rails db:migrate` rather than migrating in the build. A failure there produces `pre_deploy_failed`, and the old version keeps serving.
- **Boot:** Puma binds `0.0.0.0:$PORT` (Render defaults `PORT` to `10000`).
- **Env vars:**
  - `RAILS_MASTER_KEY` is set (Blueprint `sync: false`).
  - `DATABASE_URL` comes from `fromDatabase` → `connectionString`.
  - `REDIS_URL` comes from `fromService` with `type: keyvalue`.
- **Memory:** set `WEB_CONCURRENCY` explicitly, because an unset value can over-fork and get OOM-killed (`Killed`, exit code 137) on small instances.
- **Health check:** `healthCheckPath: /up` (the Rails 8 default route) responds without auth or a database-heavy query.

## Related Skills

- **render-deploy**: first-time deploys, generating `render.yaml`, creating services.
- **render-debug** and **render-monitor**: MCP-first debugging and monitoring guides (Codex track).
- **render-migrate-from-heroku**: moving an existing Heroku app.

## Agent Verification

Before reporting a workflow as done:

- Name the service ID and workspace you acted on.
- For any mutation, show the command or API call that ran, then confirm the result: deploy status `live` from `render deploys list <srv> -o json`, the expected env keys present, or the service responding on its health check path.
- After a recovery, tail `render logs -r <srv> --level error --limit 50 -o text` and report whether new errors appeared.
- Run `render blueprints validate` if you changed `render.yaml`.
