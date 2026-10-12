# Rails 8 Blueprint and Background Jobs

Choose and configure a background job setup for a Rails 8 app on Render, keep `render.yaml` as the infra source of truth, and stay inside the Postgres connection limit.

## When to Use

- Writing or reviewing `render.yaml` for a Rails 8 app (web service, Postgres, worker, Key Value).
- Choosing between Solid Queue in Puma, a dedicated Solid Queue worker, and Sidekiq on Key Value.
- Moving Solid Queue out of Puma, or switching job backends.
- `too many connections`, jobs not running, or jobs disappearing.

For generic first-time deploys of non-Rails stacks, use **render-deploy**.

## Inputs

- `config/puma.rb`, `config/database.yml`, `config/queue.yml`, `config/cache.yml`, `config/cable.yml`, `config/environments/production.rb`.
- The existing `render.yaml`, if any, and the Render plan of each service and the database.

## Workflow

### 1. Choose a job backend

| | Solid Queue in Puma | Solid Queue, dedicated worker | Sidekiq + Key Value |
|---|---|---|---|
| Extra Render resources | None | 1 background worker | 1 worker + 1 Key Value (paid plan for persistence) |
| Durability | Postgres (backups on paid plans) | Postgres | Key Value persistence; none on the free plan |
| Transactional enqueue | Yes (same DB) | Yes | No |
| Isolation | Competes with web for CPU and memory | Isolated, scales separately | Isolated, highest throughput |
| Postgres connections | Web pool + queue threads per instance | Worker threads count against the DB limit | Job code still uses Active Record connections |
| Must-set config | `SOLID_QUEUE_IN_PUMA` | `startCommand: bin/jobs` | `maxmemoryPolicy: noeviction` |
| Agent visibility | `query_render_postgres` on `solid_queue_*` tables | Same | `get_metrics` only; no Redis query tool, `render kv-cli` is interactive |
| Free tier | Works, but spin-down pauses jobs | No (no free workers) | No |

**Default:** Solid Queue in Puma on a single Postgres database. Move to a dedicated worker when job CPU or memory shows up in web metrics ([database and jobs](database-and-jobs.md#2-capacity-review)). Choose Sidekiq only for very high job volume, latency-sensitive jobs, or an existing Sidekiq Pro/Enterprise dependency.

### 2. Write `render.yaml`

Web service + Postgres, Solid Queue in Puma:

```yaml
services:
  - type: web
    name: mysite
    runtime: ruby
    plan: starter
    region: oregon
    buildCommand: ./bin/render-build.sh
    preDeployCommand: bin/rails db:migrate   # paid plans only; on free, migrate in the build
    startCommand: bin/rails server
    healthCheckPath: /up
    envVars:
      - key: DATABASE_URL
        fromDatabase: { name: mysite-db, property: connectionString }
      - key: RAILS_MASTER_KEY
        sync: false
      - key: WEB_CONCURRENCY
        value: "2"
      - key: RAILS_MAX_THREADS
        value: "3"
      - key: SOLID_QUEUE_IN_PUMA
        value: "true"
databases:
  - name: mysite-db
    plan: basic-256mb
    region: oregon
    ipAllowList: []          # internal connections only
```

Dedicated Solid Queue worker: remove `SOLID_QUEUE_IN_PUMA` from the web service (see step 3) and add:

```yaml
  - type: worker
    name: mysite-jobs
    runtime: ruby
    plan: starter
    region: oregon
    buildCommand: ./bin/render-build.sh
    startCommand: bin/jobs
    envVars:
      - key: DATABASE_URL
        fromDatabase: { name: mysite-db, property: connectionString }
      - key: RAILS_MASTER_KEY
        sync: false
```

Sidekiq on Key Value: use a Key Value instance only for Sidekiq, and a **separate** `allkeys-lru` instance if you also want a Redis cache store.

```yaml
  - type: keyvalue
    name: mysite-sidekiq-kv
    plan: 256mb              # smallest plan with persistence; free has none
    region: oregon
    maxmemoryPolicy: noeviction   # the default allkeys-lru silently drops jobs
    ipAllowList: []
  - type: worker
    name: mysite-sidekiq
    runtime: ruby
    plan: starter
    region: oregon
    buildCommand: bundle install
    startCommand: bundle exec sidekiq -C config/sidekiq.yml
    envVars:
      - key: REDIS_URL
        fromService: { type: keyvalue, name: mysite-sidekiq-kv, property: connectionString }
      - key: DATABASE_URL
        fromDatabase: { name: mysite-db, property: connectionString }
      - key: RAILS_MASTER_KEY
        sync: false
# Add the same REDIS_URL entry to the web service so it can enqueue.
```

The internal Key Value URL (`redis://red-...:6379`) has no auth by default and works only from the same workspace and region. Rails-side Sidekiq setup is in the **sidekiq-setup** skill.

Then:

```bash
render blueprints validate render.yaml -o json   # schema, plans, regions, name conflicts
```

The first Blueprint sync happens in the Dashboard, because `sync: false` secrets like `RAILS_MASTER_KEY` are entered there. Neither the CLI nor MCP can create a Blueprint instance, and MCP cannot create background workers.

### 3. Check `SOLID_QUEUE_IN_PUMA`

Rails 8.0.x generates `plugin :solid_queue if ENV["SOLID_QUEUE_IN_PUMA"]`, so **any non-empty value, including `"false"`, turns the plugin on**. To turn it off, delete the variable. Newer Rails treats `""`, `"false"`, and `"0"` as off; read the app's `config/puma.rb` to see which form it has.

With the plugin on, each Puma worker runs the queue's supervisor, dispatcher, and workers, which adds memory and connections per instance. On a free web service, spin-down after 15 idle minutes also stops the jobs.

### 4. Pick a database layout

**Single database (simplest on Render):**
- Queue: copy `db/queue_schema.rb` into a normal migration, delete the schema file, and remove `config.solid_queue.connects_to` from `production.rb`.
- Cable: copy `db/cable_schema.rb` into a migration and remove `connects_to` from `config/cable.yml`.
- Cache: copy `db/cache_schema.rb` into a migration (`db:migrate` won't load it) and remove `database:` from `config/cache.yml`. Cache writes then join any wrapping transaction.
- `database.yml` production becomes `<<: *default`, and `DATABASE_URL` supplies the connection.

**Multiple databases (Rails 8 default):** `DATABASE_URL` merges into `primary` only. Set `CACHE_DATABASE_URL`, `QUEUE_DATABASE_URL`, and `CABLE_DATABASE_URL`, and make sure those databases exist on the Render instance. Whether the Render-created Postgres user can `CREATE DATABASE` during `db:prepare` is unverified, so test it or create the databases by hand.

### 5. Size the queue and the connection budget

```yaml
# config/queue.yml
production:
  dispatchers:
    - polling_interval: 1
      batch_size: 500
  workers:
    - queues: "*"
      threads: 3
      processes: <%= ENV.fetch("JOB_CONCURRENCY", 1) %>
      polling_interval: 1
```

The stock `polling_interval: 0.1` generates steady database traffic. Against an **external** database this costs Render bandwidth even when idle, so always use the internal `DATABASE_URL` and raise the intervals.

Connection budget:

```
web instances × WEB_CONCURRENCY × RAILS_MAX_THREADS
+ worker processes × (threads + ~2 for supervisor, dispatcher, heartbeat)
+ one extra instance's worth during deploys
```

| Postgres RAM | Max connections |
|---|---|
| < 8 GB | 100 (legacy plans ≤ 6 GB: 97) |
| 8–16 GB | 200 |
| 16–32 GB | 400 |
| ≥ 32 GB | 500 |

Near the limit, enable PgBouncer (paid databases). It is off by default, runs in transaction mode only, and listens on port 6432. Use `prepared_statements: false` on the pooled URL, and keep migrations on the direct URL.

### 6. Switch backends safely

Jobs in flight on the old adapter are orphaned by a switch. Drain the old queue first, or run both adapters until it's empty. Changing a Key Value or Postgres plan causes brief downtime.

## Symptom → Cause → Fix

| Symptom | Likely cause | Fix |
|---|---|---|
| Jobs enqueue but never run | Plugin off, no worker, or free web service spun down | Check `SOLID_QUEUE_IN_PUMA` and `config/puma.rb`, or add a `bin/jobs` worker |
| Jobs run on the web service after "disabling" the plugin | `SOLID_QUEUE_IN_PUMA=false` on Rails 8.0.x | Delete the variable |
| `relation "solid_queue_jobs" does not exist` | Single-DB layout without the schema migration | Move `db/queue_schema.rb` into a migration (step 4) |
| `FATAL: too many connections` / `remaining connection slots are reserved` | Budget exceeds the plan's limit | Lower threads or concurrency, move jobs to a worker, or enable PgBouncer |
| Sidekiq jobs vanish | Key Value eviction policy isn't `noeviction`, or the instance is shared with a cache | Set `maxmemoryPolicy: noeviction` on a dedicated instance |
| OOM on the web service after adding jobs | In-Puma queue processes per Puma worker | Lower `WEB_CONCURRENCY` or move jobs to a worker |
| Bandwidth bill on an idle app | Fast polling against an external DB | Internal URL, higher `polling_interval` |

## Done When

- [ ] `render blueprints validate render.yaml -o json` passes.
- [ ] Exactly one job runner is configured: the Puma plugin, a `bin/jobs` worker, or Sidekiq.
- [ ] The connection budget is under the Postgres limit with a deploy's worth of headroom.
- [ ] Sidekiq Key Value (if used) has `noeviction` and is not shared with a cache.
- [ ] After deploy, jobs are processing: the backlog query in [database and jobs](database-and-jobs.md#1-read-only-sql-diagnostics) is falling, and no new rows appear in `solid_queue_failed_executions`.

## Related

- [Database and jobs operations](database-and-jobs.md)
- [Environment configuration](environment-configuration.md)
- [Deployment status and build failures](deploy-status-and-build-failures.md)
