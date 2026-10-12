# Deployment Status and Build Failures

Answer "did it deploy?" and "why did it fail?" for a Render service: read the deploy history, pull the logs for the failing phase, classify the failure, and re-run once it is fixed.

## When to Use

- A push did not show up in production, or you need to know which commit is live.
- A deploy ended in `build_failed`, `pre_deploy_failed`, `update_failed`, or `canceled`.
- A deploy has sat in `queued` or `build_in_progress` far longer than usual.
- You fixed a build problem and need to redeploy and confirm the fix.

## Inputs

- **Service name or ID** (`srv-...`). Resolve names to IDs in step 2.
- **Workspace** name or ID. Confirm it in step 1.
- **Deploy ID** (`dep-...`), if known. Otherwise take the latest one from step 3.

## Workflow

### 1. Confirm the workspace

```bash
render workspace current
render workspaces -o text          # if the service is not where you expected
render workspace set <name-or-id>
```

Check that the workspace name matches the project before you go further. Most "service not found" errors come from the wrong workspace.

### 2. Resolve the service ID

```bash
render services -o json | jq -r '.[] | (.service // .) | [.id, .name, .type] | @tsv'
SRV=srv-xxxxxxxx
```

The JSON shape can differ between CLI versions. If jq prints nothing or `null`, run `render services -o json | jq '.[0]'` first and adjust the path.

### 3. List deploys and read the latest status

```bash
render deploys list "$SRV" -o json > /tmp/deploys.json
jq '.[0]' /tmp/deploys.json                      # inspect the real field names first

# Latest deploy: id, status, trigger, times, commit
jq -r 'map(.deploy // .) | sort_by(.createdAt) | last
  | {id, status, trigger, createdAt, finishedAt,
     commit: (.commit.id // "" | .[0:7]), message: (.commit.message // "" | split("\n")[0])}' /tmp/deploys.json

# Last 10 deploys as a table
jq -r 'map(.deploy // .) | sort_by(.createdAt) | reverse | .[0:10][]
  | [.id, .status, .createdAt, (.finishedAt // "-"), (.commit.id // "" | .[0:7])] | @tsv' /tmp/deploys.json
```

`render deploys list` has no status or limit filter, so filter with jq. Field names (`status`, `createdAt`, `finishedAt`, `commit.id`) follow the REST Deploy object. If a field comes back `null`, inspect the raw object and adjust. Save the deploy ID, `createdAt`, and `finishedAt`. Step 5 uses them.

Interpret the status:

| Status | Meaning | Next step |
|---|---|---|
| `created` | Deploy record exists and has not started. | Wait briefly. If it stays here, check for an overlapping deploy (step 7). |
| `queued` | Waiting on another deploy for this service. Only one deploy runs at a time. | Find the in-progress deploy (step 7). |
| `build_in_progress` | Build command or Docker build is running. | Tail build logs (step 5). Compare against normal build time. |
| `build_failed` | Build exited non-zero or timed out. Nothing new was started. | Build logs (step 5), then classify (step 6). |
| `pre_deploy_in_progress` | Pre-deploy command (usually `db:migrate`) is running on a separate instance. | Watch build-type logs for migration output. |
| `pre_deploy_failed` | Pre-deploy command exited non-zero. The new build was not started. | Read the migration error (step 5). Fix it and redeploy. |
| `update_in_progress` | New instances are starting and must pass the health check before taking traffic. | Tail app logs for boot output. |
| `update_failed` | New instances crashed, never opened a port, or failed the health check. | App logs for the deploy window (step 5). |
| `live` | This deploy is serving traffic. | Done, unless the wrong commit is live. |
| `deactivated` | Was live and has been replaced by a newer deploy. | Nothing. This is history. |
| `canceled` | Canceled by a user, superseded by a newer deploy, or timed out waiting on the health check. | Check who or what canceled it (step 4 and step 7). |

### 4. Determine what is actually serving

A failed or canceled deploy does **not** take the site down. On `build_failed`, `pre_deploy_failed`, `update_failed`, and `canceled`, the previous `live` deploy keeps serving.

```bash
jq -r 'map(.deploy // .) | map(select(.status == "live"))
  | .[] | [.id, .createdAt, (.commit.id // "" | .[0:7])] | @tsv' /tmp/deploys.json
```

Report two things: the deploy and commit that are live, and the newer deploy that failed. If no deploy is `live`, the service is down or suspended. Switch to [failed deployment recovery](failed-deploy-recovery.md).

### 5. Pull logs windowed to the deploy

There is no deploy-ID filter on logs, so window them with the deploy's `createdAt` and `finishedAt` (RFC 3339).

```bash
START=2026-10-11T14:02:10Z   # deploy createdAt
END=2026-10-11T14:09:45Z     # deploy finishedAt (omit and use --tail if still running)

# build_failed / pre_deploy_failed: build output, oldest first
render logs -r "$SRV" --type build --start "$START" --end "$END" \
  --direction forward --limit 500 -o text

# Find the first error quickly
render logs -r "$SRV" --type build --start "$START" --end "$END" \
  --text "error,Error,failed,ERROR" --limit 100 -o text

# update_failed: boot crashes, port detection, health check
render logs -r "$SRV" --type app --start "$START" --end "$END" \
  --direction forward --limit 300 -o text

# Still running: follow live (--tail cannot be combined with --end)
render logs -r "$SRV" --type build --tail -o text
```

Read build logs from the **first** error, not the last line. The last line is usually just "exited with status 1". For `update_failed`, look for a Ruby backtrace at boot, `No open ports detected`-style messages, or repeated health check failures. Deeper log filtering is in [logs](logs.md).

### 6. Classify the failure

Match the first real error to a row in the [Symptom → Cause → Fix](#symptom--cause--fix) table. To confirm env-related causes, list env **keys** only (never values) as described in [environment configuration](environment-configuration.md).

### 7. Handle stuck deploys

- **Queued behind another deploy.** Only one deploy runs per service. Under the workspace's Overlapping Deploy Policy, **Wait** (the default for workspaces created on or after 2025-07-14) finishes the current deploy, then runs the most recent queued one and skips intermediates. **Override** cancels the in-progress deploy. Find the blocker:

  ```bash
  jq -r 'map(.deploy // .) | map(select(.status | test("progress|queued|created")))
    | .[] | [.id, .status, .createdAt] | @tsv' /tmp/deploys.json
  ```

- **Long `build_in_progress`.** Tail the build logs. If output has stopped for a long time, the usual causes are a hung asset build, a Docker step waiting on input, or a stalled network fetch.
- **Long `update_in_progress`.** The health check is not passing. Render cancels the deploy after 15 minutes and the previous deploy keeps serving. Check app logs for the boot error.

Cancelling is a mutation. **Get user approval first** and state the workspace, service ID, and deploy ID:

```bash
render deploys cancel "$SRV" dep-xxxxxxxx
```

### 8. Re-run after the fix

Triggering a deploy is a mutation. **Get explicit user approval** and name the workspace, service ID, and commit before running it.

```bash
render deploys create "$SRV" --wait                          # latest commit on the branch
render deploys create "$SRV" --commit <sha> --wait           # a specific commit
render deploys create "$SRV" --clear-cache --wait            # suspect stale build cache
```

`--wait` blocks and exits non-zero if the deploy fails, so check `$?`. Use `--clear-cache` when the cause looks like a stale Bundler, Node, or asset cache: a gem or package that "should" be there, or old assets after a pipeline change. Afterwards, rerun step 3 and confirm the new deploy is `live` with the expected commit.

### MCP and REST alternatives

| Step | Render MCP | REST (`https://api.render.com/v1`, `Authorization: Bearer $RENDER_API_KEY`) |
|---|---|---|
| Workspace | `get_selected_workspace`, `select_workspace` | n/a |
| Deploy list / detail | `list_deploys`, `get_deploy` | `GET /services/{id}/deploys`, `GET /services/{id}/deploys/{deployId}` |
| Logs | `list_logs` (type build or app, time window) | `GET /logs` |
| Phase events | `list_events` (look for `build_ended`, `deploy_ended`) | `GET /services/{id}/events` |
| Trigger (approval required) | `trigger_deploy` (`clearCache`) | `POST /services/{id}/deploys` body `{"clearCache": "clear"}` |

```bash
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/$SRV/deploys/dep-xxxxxxxx" | jq '{id, status, createdAt, finishedAt, commit: .commit.id}'
```

## Symptom → Cause → Fix

| Symptom (log or status) | Likely cause | Fix |
|---|---|---|
| `build_failed`, "command not found" or "Permission denied" on `bin/render-build.sh` | Build command wrong, or script not executable | `chmod a+x bin/render-build.sh`, commit, and check the Build Command matches. |
| `build_failed`, "Your Ruby version is X, but your Gemfile specified Y" | Ruby version not pinned or mismatched | Pin in `.ruby-version` and the `Gemfile` `ruby` line so both match. |
| `build_failed` in yarn, npm, or esbuild | Node version mismatch | Pin with `.node-version` or `NODE_VERSION`. |
| Bundler "could not find gem for platform" or native extension compile error | Lockfile lacks Linux platform, or a native gem needs system libs | `bundle lock --add-platform x86_64-linux`, commit `Gemfile.lock`. Use Docker if system packages are required. |
| `assets:precompile` fails with "Missing secret_key_base" or credentials errors | Env var missing at build time | Set `RAILS_MASTER_KEY` (or `SECRET_KEY_BASE`) on the service. See [environment configuration](environment-configuration.md). |
| Build references an env var that is empty | Var added with "Save only", or only defined in a linked env group not attached | Attach or define it, then redeploy. Docker builds get service env vars as build args. Secret files are not available at Docker build time unless mounted as Docker secrets. |
| Docker deploy hangs after build, never goes live | Image has no `CMD` or `ENTRYPOINT` | Add `CMD ["./bin/rails", "server"]` (or a Puma command) to the Dockerfile. |
| `pre_deploy_failed` | `db:migrate` error: bad migration, lock timeout, missing `DATABASE_URL` | Read the migration error, fix it, and redeploy. Prior deploy is still serving. |
| `update_failed`, no open port detected | Puma bound to `localhost` or a hardcoded port | Bind `0.0.0.0:$PORT` (default `10000`). Avoid reserved ports 18012, 18013, 19099. |
| `update_failed` or `canceled` after about 15 min in update | Health check never passed | Make `healthCheckPath` (for example `/up`) return 200 without auth, redirects, or heavy DB work. |
| `update_failed`, backtrace at boot | App crashes on boot: missing env var, bad initializer, credentials | Fix from the app log backtrace, then redeploy. |
| Build log ends abruptly with "Killed" or exit 137 | Possibly OOM during build, for example asset compile (unverified for builds) | Reduce build memory (limit Node workers, precompile fewer bundles), or try a larger plan (unverified). |
| Stale gems or old assets despite a fix | Build cache | Redeploy with `--clear-cache` (approval required). |
| Deploy stuck in `queued` | Another deploy in progress, Wait policy | Let it finish, or cancel the blocker with approval. |

## Rails Notes

- Keep `bin/render-build.sh` minimal: `set -o errexit`, `bundle install`, `bin/rails assets:precompile`, `bin/rails assets:clean`. Run `db:migrate` there only on free plans.
- On paid plans, use `preDeployCommand: bundle exec rails db:migrate`. A failure gives `pre_deploy_failed` rather than a half-migrated live app. Pre-deploy runs on a separate instance with no disk.
- `assets:precompile` boots the app, so any initializer that reads credentials needs `RAILS_MASTER_KEY` at build time. Do not print it to confirm. Check that the key exists.
- Puma: `port ENV.fetch("PORT", 10000)` and bind `0.0.0.0`. Set `WEB_CONCURRENCY` explicitly.
- Rails 7.1+ and 8 ship `/up`. Make sure `config.force_ssl` or host authorization does not redirect or block the health check.
- A Gemfile change that compiles locally on macOS can still fail on Linux. Always commit the Linux platform in `Gemfile.lock`.

## Done When

- [ ] Workspace and service ID are stated.
- [ ] The latest deploy's ID, status, commit, and timestamps are reported.
- [ ] The deploy and commit currently serving traffic are identified.
- [ ] For a failure, the first real error line from build or app logs is quoted (secrets redacted) and mapped to a cause.
- [ ] The fix is applied in code or config, or handed to the right workflow.
- [ ] Any redeploy or cancel had explicit user approval, and the new deploy shows `live` with the expected commit.

## Related

- [logs](logs.md): deeper log filtering, request logs, OOM and restart signals.
- [environment configuration](environment-configuration.md): missing or wrong env vars, secret files, env groups.
- [failed deployment recovery](failed-deploy-recovery.md): rollback and restoring service when production is broken.
