# Failed Deployment Recovery

Get production back to a known-good state after a bad release or a failed deploy, then reconcile the side effects. Triage first, pick one recovery path, verify, and write it up.

## When to Use

- A deploy ended in `build_failed`, `pre_deploy_failed`, `update_failed`, or `canceled`, and someone needs a way forward.
- A deploy went `live` and production is now broken: 5xx spike, boot crash, bad migration, bad env var.
- Instances are crash-looping or OOM-killed right after a release.
- A deploy is stuck in `build_in_progress` or `update_in_progress` and is blocking the next fix.

For reading the failure itself (build output, deploy status), start with [deploy-status-and-build-failures.md](deploy-status-and-build-failures.md) and come back here to recover.

## Inputs

- Workspace (`render workspace current`) and service ID (`srv-...`).
- The failing deploy ID (`dep-...`) and its status.
- The last known-good deploy ID and its commit SHA.
- Whether the failing release included migrations, and whether any of them are destructive (drop/rename column or table).
- Explicit user approval before every step marked **requires user approval**.

## Workflow

### 1. Triage (2 minutes): is production actually down?

```bash
render workspace current
render deploys list <srv> -o json \
  | jq 'map(.deploy // .) | sort_by(.createdAt) | reverse | .[0:5][] | {id, status, commit: .commit.id, createdAt, finishedAt}'
curl -s -o /dev/null -w '%{http_code}\n' https://<your-domain>/up
```

Read the newest deploy status and the health check response together:

- **No outage.** `build_failed`, `pre_deploy_failed`, `update_failed`, or a deploy `canceled` after the 15-minute health check timeout. Render never switched traffic, so the previous `live` deploy is still serving. Fix forward calmly (step 3). Do not roll back; there is nothing to roll back from.
- **Outage.** The newest deploy is `live` and `/up` fails, 5xx rates jumped, or instances keep restarting. Causes: bad code, a bad migration, a bad env var, or crash-loop/OOM after going live. Restore service first (steps 4 to 7), root-cause second.

Confirm crash loops and OOM before choosing a path:

```bash
render logs -r <srv> --level error --start 30m --limit 100 -o text
render logs -r <srv> --text "Killed,exit code 137,Out of memory" --start 1h -o text
render logs -r <srv> --type request --status-code 500,502,503,504 --start 30m --limit 50 -o text
```

Events (`server_failed` with `details.reason.oomKilled`) are not in the CLI: use MCP `list_events` or `GET /services/{id}/events`. See [logs.md](logs.md).

### 2. Pick one recovery path

| Situation | Path | Step |
|---|---|---|
| Deploy stuck in progress, or a bad deploy is still building | Cancel it | 3 |
| Old deploy still serving (`build_failed`, `pre_deploy_failed`, `update_failed`) | Fix forward | 3 |
| Bad release is `live`, fix not ready in minutes | Roll back (API or dashboard) | 4 |
| Bad release is `live`, old artifact not retained, or you want a fresh build of a known-good SHA | Redeploy known-good commit | 5 |
| Build fails on stale gems/assets/node_modules with no code cause | Clear build cache + redeploy | 5 |
| Same release worked earlier; instances stuck, wedged, or a transient dependency blip | Restart | 6 |
| Users must not hit the app while you repair data or migrations | Maintenance mode | 7 |
| A recent env var change broke it (no code change) | Env var revert | 8 |

Before any mutating step, post a proposal naming the workspace, service ID, the exact command, and the expected result. Wait for approval.

### 3. Cancel a stuck deploy, then fix forward

**Requires user approval.**

```bash
render deploys cancel <srv> <deployId>
```

Then fix the cause on a branch, merge, and let auto-deploy ship it (or trigger it in step 5). For `pre_deploy_failed`, check migration state first (see Rails Notes).

### 4. Roll back to a previous deploy

There is no CLI command and no MCP tool for rollback. Use the dashboard or the REST API. When the live release is crash-looping, the guarded script in [guarded-remediation.md](guarded-remediation.md) automates this step (auto-deploy off first, then rollback) and verifies the result.

**Dashboard:** Service, then Deploys, then Rollback on the known-good deploy. This **disables auto-deploy** automatically.

**API (requires user approval).** The API rollback does **not** disable auto-deploy, so the next push to the branch would re-ship the bad commit. Disable it first:

```bash
# 1. Stop the next push from re-deploying the bad commit (requires user approval)
render services update <srv> --auto-deploy=false -o json

# 2. Roll back to the known-good deploy (requires user approval); expect HTTP 201 + a Deploy object
curl -s -X POST "https://api.render.com/v1/services/<srv>/rollback" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"deployId":"dep-..."}'
```

What a rollback does:

- Creates a **new deploy** that reuses the old build artifact (skips the build).
- **Restores:** start command, health check path, Docker command, build artifact, instance count, and the service's own env vars as they were at that deploy.
- **Keeps current:** env **group** values, disks, plan, custom domains, static headers and redirects.
- Works only for deploys whose artifacts are still retained (plan-dependent). If the target is gone, use step 5.
- Does **not** roll back database migrations. Read Rails Notes before rolling back past a migration.

### 5. Redeploy a known-good commit (optionally clearing the build cache)

**Requires user approval.** This rebuilds from source and does not change the auto-deploy setting (unlike the dashboard's "Deploy a specific commit", which disables it).

```bash
render deploys create <srv> --commit <sha> --wait
render deploys create <srv> --clear-cache --wait        # stale cache, current commit
render deploys create <srv> --commit <sha> --clear-cache --wait
```

`--wait` exits non-zero if the deploy fails. If auto-deploy is still on, a push during recovery will queue another deploy; consider `--auto-deploy=false` first.

### 6. Restart

**Requires user approval.**

```bash
render restart <srv>
```

A restart is a zero-downtime redeploy of the **same commit and config**. It does not apply env var changes saved since the last deploy and does not fix bad code. Use it for transient failures and stuck or wedged instances. Cron jobs cannot be restarted.

### 7. Maintenance mode

**Requires user approval** to turn on and to turn off.

```bash
render services update <srv> --maintenance-mode -o json
render services update <srv> --maintenance-mode --maintenance-mode-uri https://status.example.com -o json
render services update <srv> --maintenance-mode=false -o json      # turn off when recovered
```

Pass `--maintenance-mode-uri` together with `--maintenance-mode`. Confirm the state in the dashboard after turning it off, because the CLI's handling of `--maintenance-mode=false` is unverified.

### 8. Revert an env var

If the only change was an env var, revert that key instead of rolling back code. Use the single-key path, never the collection `PUT`, and remember which paths deploy and which do not. Follow [environment-configuration.md](environment-configuration.md).

### 9. Verify and close out

```bash
render deploys list <srv> -o json \
  | jq 'map(.deploy // .) | sort_by(.createdAt) | last | {id, status, commit: .commit.id}'
curl -s -o /dev/null -w '%{http_code}\n' https://<your-domain>/up
render logs -r <srv> --level error --limit 50 -o text
```

Then work through **Done When** and write the incident note.

## Symptom → Cause → Fix

| Symptom | Likely cause | Fix |
|---|---|---|
| `build_failed`, site still up | Build error; old deploy still serving | Fix forward; see [deploy-status-and-build-failures.md](deploy-status-and-build-failures.md) |
| `pre_deploy_failed`, site still up | `db:migrate` failed; old code still running | Check partial migration state, fix migration, redeploy |
| `update_failed` or `canceled` after ~15 min | New instances never passed the health check | Fix boot or `/up`; old deploy still serving |
| Deploy stuck in `build_in_progress` | Hung build step (for example a Docker image without CMD) | Cancel (step 3), fix, redeploy |
| `live` but 5xx everywhere | Bad code | Roll back (step 4) or redeploy known-good SHA (step 5) |
| `live`, errors like `PG::UndefinedColumn` | Code and schema out of step | Fix forward, or roll back only if schema is still compatible |
| `live`, `Killed` / exit code 137 loop | OOM, often unset `WEB_CONCURRENCY` | Roll back or set `WEB_CONCURRENCY` and redeploy; see [logs.md](logs.md). [guarded-remediation.md](guarded-remediation.md) automates the step-down with verification |
| Boot fails with `ActiveSupport::MessageEncryptor::InvalidMessage` or missing credentials | Wrong or missing `RAILS_MASTER_KEY` | Revert env var (step 8) |
| Bad commit re-deployed after rollback | API rollback left auto-deploy on | `--auto-deploy=false`, roll back again, merge the fix |
| Rollback target missing from the dashboard | Artifact no longer retained | Redeploy the SHA (step 5) |
| Restart did not pick up a new env var | Restart reuses the last deploy's config | Trigger a deploy instead (step 5) |
| Env group change still broken after rollback | Rollback does not restore env group values | Revert the group value manually |

## Rails Notes

**A Render rollback never rolls back the database.** The old code runs against the new schema. Plan for that:

- **Expand/contract migrations.** Ship additive changes first (add column, backfill, dual-write), deploy the code that uses them, and only drop or rename in a later release. Then any single release can be rolled back safely.
- **Never roll back code past a destructive migration.** If the bad release dropped or renamed a column the old code reads, rollback makes things worse. Fix forward instead.
- **`bin/rails db:rollback` only with explicit user approval**, run from a shell on the service, after confirming the target version and taking a backup:

```bash
render ssh <srv>                     # interactive; paid plans only
bin/rails db:migrate:status          # read-only: see which versions are up
bin/rails db:rollback STEP=1         # requires user approval
```

- **`pre_deploy_failed` means the migration failed and old code still runs.** Check for partial state with `bin/rails db:migrate:status` or a read-only query (MCP `query_render_postgres`, or `render psql <db-id> -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 5"`). Postgres DDL is transactional, so a normal migration that fails is rolled back in full. Migrations with `disable_ddl_transaction!` (for example `add_index ... algorithm: :concurrently`) are not, and can leave an `INVALID` index or half-applied changes to clean up before retrying.
- On free plans migrations run inside `bin/render-build.sh`, so a migration failure shows up as `build_failed` instead.
- Keep `/up` cheap and auth-free so a healthy rollback actually passes the health check.
- After an OOM incident, set `WEB_CONCURRENCY` explicitly rather than relying on the CPU-derived default.

## Done When

- [ ] `render deploys list <srv> -o json` shows the intended deploy as `live` (right commit SHA).
- [ ] `/up` returns 200 and the health check passes in the dashboard.
- [ ] Error rate and 5xx back to baseline (logs; MCP `get_metrics` for HTTP and memory).
- [ ] No new `Killed` / exit code 137 or crash-loop entries in the last 30 minutes.
- [ ] Maintenance mode is off, if it was turned on.
- [ ] Auto-deploy re-enabled once the fix is merged (requires user approval): `render services update <srv> --auto-deploy=true -o json`.
- [ ] Env drift reconciled: a rollback restored old service env vars, so re-apply any intended changes and confirm env group values.
- [ ] Migration state matches the running code.
- [ ] Incident note written:

```markdown
## Incident: <service> <date>
- Timeline (UTC): detected HH:MM, mitigated HH:MM, resolved HH:MM
- Impact: who/what was affected, duration, error counts
- Root cause: the change and why it failed
- Fix: recovery path used (rollback / redeploy / restart / env revert), deploy IDs
- Follow-ups: tests, migration policy, alerts, owners
```

## Related

- [deploy-status-and-build-failures.md](deploy-status-and-build-failures.md): read deploy status and build output.
- [logs.md](logs.md): app, request, and build logs, OOM and restart events.
- [environment-configuration.md](environment-configuration.md): revert and audit env vars, env groups, secret files.
