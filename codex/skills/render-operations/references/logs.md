# Application and Infrastructure Logs

Find out what a Render service is doing: errors, slow or failing requests, crashes, OOM kills, restarts, and cron, worker, or datastore output. Read-only throughout.

## When to Use

- Users report errors or 5xx responses, or a specific request failed.
- Requests are slow, or the error rate spiked after a release.
- Instances restart, crash-loop, or get OOM-killed.
- A cron job, background worker, Postgres, or Key Value instance misbehaves.

For a failed build or a deploy that never went live, start with [deploy-status-and-build-failures.md](deploy-status-and-build-failures.md).

## Inputs

- Workspace (`render workspace current`) and service ID(s): `srv-...` web/worker, `crn-...` cron, Postgres and Key Value IDs.
- Time of the incident (UTC), or a relative window like `1h`.
- Optional: a request ID (`Rndr-Id` response header), path, status code, or instance ID.

Logs can contain secrets (tokens, `DATABASE_URL`, auth headers, params). Never paste raw log lines that include them; redact before quoting.

## Workflow

### 1. Resolve IDs and pick the log type

```bash
render services -o json | jq -r '.[] | [.service.id // .id, .service.name // .name, .service.type // .type] | @tsv'
render services instances <srv> -o json      # instance IDs for --instance
```

The jq paths above are a convenience (the JSON shape is unverified); fall back to reading `-o json` directly.

| Type | Contains | Use for |
|---|---|---|
| `app` | stdout/stderr of the running process (Rails, Puma, Solid Queue, Sidekiq) | exceptions, boot errors, crash output |
| `request` | one line per HTTP request at Render's edge: method, path, status, `responseTimeMS`, `requestID` | 5xx rates, slow paths, correlating a user report |
| `build` | build command output | build failures (see the deploy workflow) |

### 2. Run the filter recipes

`-r` is required non-interactively. Default `--limit` is 100.

```bash
# Recent errors
render logs -r <srv> --level error --limit 50 -o text

# Time window: relative, or absolute RFC3339 (UTC)
render logs -r <srv> --start 1h -o text
render logs -r <srv> --start 2026-10-11T14:00:00Z --end 2026-10-11T14:30:00Z --limit 500 -o text

# Oldest first inside the window
render logs -r <srv> --start 30m --direction forward -o text

# Tail live (cannot be combined with --end); Ctrl-C to stop
render logs -r <srv> --tail -o text

# Text search (comma-separated values)
render logs -r <srv> --text "ActiveRecord::RecordNotFound,PG::ConnectionBad" --start 2h -o text

# 5xx responses
render logs -r <srv> --type request --status-code 500,502,503,504 --start 1h -o text

# A specific path and method
render logs -r <srv> --type request --path /checkout --method POST --start 1h -o text

# One instance only
render logs -r <srv> --instance <instance-id> --start 30m -o text

# Several resources at once (web + worker), which the dashboard cannot do
render logs -r <srv-web>,<srv-worker> --level error --start 1h -o text
```

There is no deploy-ID filter. To see logs for one deploy, take `createdAt`/`finishedAt` from `render deploys list <srv> -o json` and pass them as `--start`/`--end`.

### 3. Parse JSON output with jq

`-o json` emits one JSON object per log line with `id`, `timestamp`, `message`, and `labels` (a list of `{name, value}`).

```bash
render logs -r <srv> --level error --start 1h -o json \
  | jq -r '"\(.timestamp)  \(.message)"'

# Flatten labels to see what is available (level, type, instance, ...)
render logs -r <srv> --type request --limit 5 -o json \
  | jq -c '{timestamp, message, labels: (.labels | map({(.name): .value}) | add)}'

# Count error messages by first 80 chars
render logs -r <srv> --level error --start 6h --limit 1000 -o json \
  | jq -r '.message[0:80]' | sort | uniq -c | sort -rn | head -20
```

Label names beyond the documented filters are (unverified); inspect them with the second command before filtering on them.

### 4. Correlate a user report by request ID

Every response carries an `Rndr-Id` header, which equals `requestID` in request logs.

```bash
curl -sI https://<app-host>/ | grep -i '^rndr-id'
render logs -r <srv> --type request --text <rndr-id> --start 2h -o json
```

If `--text` does not match the ID (unverified whether it searches request-log fields), narrow by time, path, and status instead and match `requestID` in the jq output. Then pull `app` logs for the same instance and a window of a few seconds around that timestamp.

### 5. Check infrastructure signals the CLI cannot show

Service events (no CLI command): MCP `list_events`, or REST:

```bash
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/<srv>/events" | jq '.[] | .event // .'
```

The response wrapper shape (`.event`) is (unverified); the `// .` fallback prints the raw item.

What to look for:

- `server_failed` with `details.reason`:
  - `oomKilled.memoryLimit`: out of memory.
  - `nonZeroExit`: process exited with that code (crash, bad boot).
  - `unhealthy`: health check failed long enough to restart.
  - `evicted` / `evictionReason`: platform moved the instance.
  - `timedOutReason` / `timedOutSeconds`: start or health timeout.
- `server_restarted`: instance restarted (after a failure or `render restart`).
- `autoscaling_ended`: instance count changed.
- `deploy_started` / `deploy_ended`, `build_started` / `build_ended`: line errors up against releases.
- `cron_job_run_ended`: cron outcome.

Metrics (no CLI command): MCP `get_metrics`, or `GET /metrics/{cpu,memory,memory-limit,http-requests,http-latency,instance-count}`. Query parameter names such as `resource`, `startTime`, `endTime` are (unverified); check the API reference before scripting.

- Memory climbing toward `memory-limit` then dropping sharply: OOM kill and restart.
- CPU pinned at `cpu-limit`: undersized instance or a hot loop.
- `http-latency` rising with flat `http-requests`: slow dependency (DB, external API).
- `instance-count` changes lining up with errors: autoscaling or cold instances.

### 6. Diagnose OOM and crash loops

```bash
render logs -r <srv> --text "Killed,exit code 137,Out of memory,cannot allocate memory" --start 24h -o text
render logs -r <srv> --type app --start 30m --direction forward -o text   # boot sequence after restart
```

Confirm with `server_failed` events carrying `oomKilled` and with the memory metric. A crash loop shows repeated `server_failed` plus `server_restarted` events and the same boot error each time; read the first error after each boot, not the last.

Once confirmed, [guarded-remediation.md](guarded-remediation.md) can plan and apply a `WEB_CONCURRENCY` step-down (or a rollback of a crash-looping release) with guards and verification.

### 7. Cron jobs, workers, and datastores

```bash
render logs -r <crn-id> --start 1d -o text           # cron job output
render logs -r <srv-worker> --level error --start 1h -o text
render logs -r <dpg-id> --start 1h -o text           # Postgres
render logs -r <kv-id> --start 1h -o text            # Key Value
```

- Cron: the dashboard Runs page shows each run with its own logs and status; use it to find the run, then the CLI for the window.
- Workers have no request logs; rely on `app` logs, events, and memory metrics.
- Datastore logs show connection limits, slow queries, and restarts. For read-only queries use `render psql <db-id> -c "..."` or MCP `query_render_postgres`.

### 8. Inspect a live instance with `render ssh`

```bash
render ssh <srv>                 # interactive only, paid plans
render ssh <srv> --ephemeral     # fresh instance: no traffic, start command not run
```

Use it to check memory (`ps`, `free`), files, or run `bin/rails runner` against production. Prefer `--ephemeral` for experiments so live traffic is unaffected. The agent cannot drive it non-interactively; hand the command to the user.

### 9. Know the limits

- Retention: Hobby 7 days, Pro 14 days, Scale and Enterprise 30 days.
- App logs are capped at 6,000 lines per minute per instance; excess lines are dropped silently. Gaps during a spike may be the cap, not the app.
- For longer retention or real search, set up a log stream (syslog RFC5424 over TLS) to a provider such as Datadog, Better Stack, or Papertrail.
- The dashboard log search supports wildcards, `/regex/`, and filters like `status_code:/5../`.

## Symptom → Cause → Fix

| Symptom | Likely cause | Fix |
|---|---|---|
| `Killed` / exit code 137, `server_failed` with `oomKilled` | Memory over the instance limit | Set `WEB_CONCURRENCY` explicitly, lower Puma threads or worker job concurrency, or move to a larger plan |
| Repeated `server_failed` with `nonZeroExit` right after deploy | Boot error (missing env var, bad migration state, gem load error) | Read the first app error after boot; see [environment-configuration.md](environment-configuration.md) or [failed-deploy-recovery.md](failed-deploy-recovery.md) |
| `server_failed` with `unhealthy` | Health check path slow, auth-protected, or DB-dependent | Point `healthCheckPath` at `/up`; keep it cheap |
| 502/503 in request logs, quiet app logs | Instances restarting or not bound to `0.0.0.0:$PORT` | Check events for restarts; confirm Puma bind |
| High `responseTimeMS` on a few paths | N+1 queries, missing index, slow external call | Filter by `--path`, check Postgres logs and `http-latency` |
| Gaps in logs during a traffic spike | 6,000 lines/min/instance cap | Lower log volume (`info` level, lograge); add a log stream |
| No logs older than a week or two | Plan retention reached | Use a log stream for history |
| Worker jobs silently failing | Errors only in worker service | Query the worker ID, not the web ID; use `-r web,worker` |
| `PG::ConnectionBad` / too many connections | Pool size times processes exceeds DB limit | Align `RAILS_MAX_THREADS`, `WEB_CONCURRENCY`, and DB plan |

## Rails Notes

- Recent Rails `production.rb` logs to STDOUT with `config.log_level = ENV.fetch("RAILS_LOG_LEVEL", "info")`. Keep `info` in production; `debug` floods logs and hits the line cap.
- Rails tags lines with `:request_id` (from `X-Request-Id` or a generated UUID). It does **not** automatically equal Render's `Rndr-Id`. Suggestion: add a log tag that captures Render's ID if it is present on the incoming request (unverified that Render forwards it), otherwise correlate by timestamp, path, and instance.
- Suggestion: use `lograge` (one line per request) or JSON logging so lines are greppable with `--text` and parseable with jq.
- Multi-line backtraces arrive as separate log lines; widen the window and use `--direction forward` to read them in order.
- `config.filter_parameters` masks params in Rails logs but not in Render request logs or your own `puts`; never log tokens or full env.
- Solid Queue or Sidekiq run as a separate worker service: check its logs and memory independently of the web service.

## Done When

- [ ] Workspace and service ID(s) are named.
- [ ] The failing window is identified (UTC start and end) and tied to a deploy or not.
- [ ] Root signal found: an app error, a request pattern, or an event (`server_failed` reason, restart, autoscaling).
- [ ] OOM or crash-loop confirmed or ruled out with events and memory metrics.
- [ ] Quoted log lines are redacted of secrets.
- [ ] A next step is proposed (fix, env change, rollback) and handed to the right workflow; nothing mutated without approval.

## Related

- [deploy-status-and-build-failures.md](deploy-status-and-build-failures.md)
- [environment-configuration.md](environment-configuration.md)
- [failed-deploy-recovery.md](failed-deploy-recovery.md)
