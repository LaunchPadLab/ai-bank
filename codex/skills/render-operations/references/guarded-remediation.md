# Guarded Remediation

Apply a scripted fix for two known Render issues, an OOM crash loop and a broken live release, without improvising API calls. `render_remediate.py` splits the work into a read-only `plan` that writes a reviewable `plan.md`, and an `apply` that re-checks every guard, makes only allowlisted changes, verifies the result, and logs each call.

## When to Use

- `server_failed` events with `oomKilled` keep repeating and the fix is fewer Puma workers.
- The newest deploy went `live` and has crashed or failed health checks repeatedly since, and an earlier deploy exists to roll back to.
- You diagnosed one of these with [logs.md](logs.md) or [failed-deploy-recovery.md](failed-deploy-recovery.md) and want the fix applied with guards and verification instead of by hand.

For anything else (env var reverts, cache-clearing redeploys, maintenance mode), follow [failed-deploy-recovery.md](failed-deploy-recovery.md) directly.

## Inputs

- Service ID (`srv-...`) of a web service, private service, or background worker. Other service types are never matched.
- `RENDER_API_KEY` exported in the environment. The script exits 1 without it.
- The workspace confirmed with `render workspace current`, and the service confirmed to belong to it.
- Explicit user approval of the specific plan before any `apply` without `--dry-run`.

## Workflow

### 1. Generate a plan (read-only)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/render_remediate.py plan --service <srv>              # default window 2h
python3 ${CLAUDE_SKILL_DIR}/scripts/render_remediate.py plan --service <srv> --window 6h  # 30m, 2h, 1d, ...
```

`plan` only sends GET requests, so it is safe to run without approval. It reads the service, the last 30 days of deploys, `server_failed` events inside the window, the single `WEB_CONCURRENCY` key, and best-effort memory metrics. It writes `plan.json` and `plan.md` to `~/.render-remediation/plans/<srv>-<stamp>/` (override with `--out <dir>`).

| Exit | Meaning |
|---|---|
| 0 | No known issue detected. Nothing written. Fall back to [logs.md](logs.md). |
| 2 | Issue found and a plan written. It may contain automatic actions or only manual steps. |
| 1 | Error: missing `RENDER_API_KEY`, API failure, or network error. |

### 2. Review plan.md with the user

Read `plan.md` and show the user, in order: the summary, the evidence table, the proposed actions (each with its exact API call and CLI or dashboard equivalent), the risks, the reviewer checklist, and the revert steps.

For `oom-crash-loop`, check the app repo before asking for approval and report what you find:

```bash
grep -n "WEB_CONCURRENCY\|workers" config/puma.rb
```

If `config/puma.rb` does not derive `workers` from `WEB_CONCURRENCY`, say so: the change may have no effect, so confirm how the Puma version in `Gemfile.lock` picks its worker count before going further.

For `bad-live-deploy`, check whether the bad release shipped migrations (see Rails Notes) and tick the checklist item only when it did not ship a destructive one.

### 3. Get explicit approval for that plan

Ask for approval naming the workspace, the service ID, the detector, and each action in order, for example: "Approve plan `<path>` on `srv-abc` in workspace Acme: set `WEB_CONCURRENCY=2`, then deploy?" Approval covers that plan file only. A re-generated plan needs a fresh review and fresh approval.

### 4. Dry run, then apply

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/render_remediate.py apply --plan <dir>/plan.json --confirm <srv> --dry-run
python3 ${CLAUDE_SKILL_DIR}/scripts/render_remediate.py apply --plan <dir>/plan.json --confirm <srv>
```

`--dry-run` runs every guard, including a fresh read of the live service, and prints the requests it would send. Nothing is changed. Run it first and show the output.

The real `apply` re-runs the guards, sends the allowlisted requests in plan order, then waits for the new deploy to go `live` (polling every 15 seconds, up to 20 minutes) and watches for failures for `--verify-minutes` (default 5). It can block for about 25 minutes, so run it where a long command will not be killed and read its output when it exits.

### 5. Read the verification result

| Exit | Meaning | Next step |
|---|---|---|
| 0 | Applied, new deploy `live`, no new failures in the watch window. | Record the outcome (step 6). |
| 4 | Applied, but the deploy failed, timed out, or new failures appeared. | The script changed nothing further. Show the printed revert steps, get fresh approval, and run them by hand. |
| 3 | `REFUSED` by a guard. Nothing sent. | See Symptom → Cause → Fix. |
| 1 | Error before any change (missing key, unreadable plan, API error during the guard checks), or a mutating request failed partway. On a partial failure the script audits the error, prints `Completed before the failure: ...` and the revert steps, and sends nothing further. | Read which actions completed, check `render deploys list <srv> -o json` and auto-deploy, then pick the next step with the user. |

Verification for `oom-crash-loop` counts only new OOM kills. Verification for `bad-live-deploy` counts any new `server_failed` event.

### 6. Record the outcome

Read the audit trail and write the incident note from the template at the end of [failed-deploy-recovery.md](failed-deploy-recovery.md). List the plan path, deploy IDs, and the verification result.

```bash
tail -n 20 ~/.render-remediation/audit.jsonl | jq -c .
```

Each line records the time, service, detector, action, request, HTTP status, and deploy ID (or the error for a failed request), plus a final `verify` record after a completed run. The file is created with mode `600`.

## Detectors

Detectors run in this order, and the first match wins.

| Detector | Signal | Automatic action | Refuses / plan-only when |
|---|---|---|---|
| `oom-crash-loop` | 2 or more `server_failed` events with `oomKilled` in the window | Set `WEB_CONCURRENCY` one lower (or pin it to 1 on 1 GB or smaller instances and 2 on larger ones if unset), then trigger a deploy without clearing the cache | `WEB_CONCURRENCY` is already 1 or lower, or holds a non-integer value. The plan lists manual steps: a larger plan, fewer threads, jemalloc, or a leak hunt. |
| `bad-live-deploy` | Newest deploy is `live`, went live inside the window, and has 3 or more non-OOM failures since (`nonZeroExit`, `unhealthy`, `earlyExit`, timeouts) | Turn auto-deploy off (only if it is on), then roll back to the most recent earlier `deactivated` deploy | No earlier deactivated deploy exists, or the live deploy is itself a rollback. |

If the OOM kills began after the newest deploy went live, the OOM plan adds a risk noting that a rollback may be the better fix. Weigh that with the user before approving.

## Guards

`apply` checks all of these before sending anything, and exits 3 on the first failure:

- **Plan version** matches the script, so an old or foreign file cannot be replayed.
- **Plan age** is under 30 minutes. The evidence goes stale fast during an incident.
- **Typed confirmation**: `--confirm` must equal the plan's service ID, which catches a wrong target.
- **Well-formed plan**: the file must be a JSON object with a state fingerprint, and every action must be an object. A truncated or hand-built file is refused.
- **Non-empty actions**: a plan with only manual steps cannot be applied.
- **Action allowlist**: only four kinds, each with exact parameters. `patch_auto_deploy` (yes or no), `rollback` (a `dep-...` ID), `set_env_var` (key `WEB_CONCURRENCY`, integer 1 to 32), and `trigger_deploy` (clear or keep cache). The script builds each request from the action kind, so the plan never carries raw API paths.
- **State fingerprint**: the latest deploy ID and status, auto-deploy, suspension, and `WEB_CONCURRENCY` must match what the plan saw. Anything that changed means the plan no longer describes production.
- **No deploy in progress**: refuses while the newest deploy is `created`, `queued`, or any `*_in_progress` status.

### What it never does

- Delete anything: services, env vars, deploys, or datastores.
- `PUT` the env-vars collection. It only writes the single `WEB_CONCURRENCY` key.
- Change any env key other than `WEB_CONCURRENCY`.
- Read any other env value. It fetches only the `WEB_CONCURRENCY` key, never the list.
- Take further automatic action after a failed request or failed verification. It prints the revert steps and stops.
- Roll back a deploy that is itself a rollback.

## Symptom → Cause → Fix

| Symptom | Likely cause | Fix |
|---|---|---|
| `REFUSED: service changed since the plan was made (...)` | A deploy, auto-deploy toggle, or env change happened after `plan` | Re-run `plan`, review the new `plan.md`, and get fresh approval |
| `REFUSED: plan expired at ...` | More than 30 minutes since `plan` | Re-run `plan`; never edit `expiresAt` |
| `REFUSED: --confirm ... does not match` | Typo, or the wrong plan file for this service | Check the service ID in `plan.md`; pass it exactly |
| `REFUSED: plan has no automatic actions` | Detector found the issue but no safe automatic step | Walk the user through the plan's manual steps |
| `REFUSED: deploy ... is build_in_progress` (or similar) | Another deploy is running | Wait for it to finish, then re-run `plan` |
| `REFUSED: action ... outside the allowlist`, `plan has no state fingerprint`, or `... is not a JSON object` | `plan.json` was edited by hand, truncated, or not produced by `plan` | Discard it and re-run `plan` |
| Exit 4, deploy ended `update_failed` after a rollback | Old build fails against the current schema or env groups | Fix forward; check migrations and env group values |
| Exit 4, new OOM kills after the step-down | One fewer worker was not enough, or `puma.rb` ignores `WEB_CONCURRENCY` | Re-run `plan` after review, or move to a larger plan (manual) |
| Exit 1 after `patch_auto_deploy` completed, `rollback ... FAILED` | Rollback API failed, for example the target's artifact is no longer retained | Auto-deploy is now off. With approval, redeploy a known-good commit per [failed-deploy-recovery.md](failed-deploy-recovery.md); re-enable auto-deploy once the fix is merged |
| Exit 1 after `set_env_var` completed, `trigger_deploy ... FAILED` | Deploy request failed; the new `WEB_CONCURRENCY` is saved but not live | With approval, run `render deploys create <srv> --wait`, or revert the key per the printed steps |
| Exit 1 partway with "may or may not have reached Render" | Network error during a mutating request | Read `audit.jsonl` and the `Completed before the failure` line, then check deploy, env, and auto-deploy state in the dashboard before retrying |
| Exit 0 from `plan` with no plan written | Fewer events than the thresholds in the window | Widen `--window` or diagnose with [logs.md](logs.md) |

## Rails Notes

- **`WEB_CONCURRENCY` and Puma workers.** Each Puma worker is a full copy of the app, so memory scales with workers times per-process size. Puma config generated by Rails 7.1 reads it, for example `workers ENV.fetch("WEB_CONCURRENCY") { 1 }`. Newer generators may not, so always check `config/puma.rb` (step 2).
- **Threads multiply connections.** Total DB connections are roughly workers times `RAILS_MAX_THREADS`. Lowering workers also lowers that, which can be a side benefit on small Postgres plans.
- **Background workers.** Solid Queue and Sidekiq size their own concurrency. A `WEB_CONCURRENCY` step-down on a worker service only helps if its process reads that key.
- **Rollback does not revert migrations.** Before approving a `bad-live-deploy` plan, list migrations between the two commits:

```bash
git log --oneline <good-sha>..<bad-sha> -- db/migrate
```

If any migration dropped or renamed a column the old code reads, do not roll back. Fix forward instead. Expand/contract migrations keep every release rollback-safe; see [failed-deploy-recovery.md](failed-deploy-recovery.md).

- **Auto-deploy stays off after a rollback.** Re-enable it only once the fix is merged, with approval: `render services update <srv> --auto-deploy=true -o json`.

## Done When

- [ ] Workspace and service ID named; `plan.md` reviewed with the user, including risks and checklist.
- [ ] For `oom-crash-loop`, the `WEB_CONCURRENCY` usage in `config/puma.rb` was reported.
- [ ] The user approved that specific plan, and `--dry-run` ran first.
- [ ] `apply` exited 0, or on exit 4 the revert steps were run by hand with fresh approval.
- [ ] `render deploys list <srv> -o json` shows the expected deploy `live`.
- [ ] Auto-deploy state is known and a follow-up exists to re-enable it if it was turned off.
- [ ] The audit log was read and the incident note written.

## Related

- [deploy-status-and-build-failures.md](deploy-status-and-build-failures.md): read deploy status and build output.
- [logs.md](logs.md): confirm OOM kills and crash loops with logs, events, and metrics.
- [environment-configuration.md](environment-configuration.md): change or revert env vars by hand.
- [failed-deploy-recovery.md](failed-deploy-recovery.md): manual recovery paths and the incident note template.
