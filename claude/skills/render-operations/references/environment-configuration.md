# Environment Configuration

Inspect, change, audit, and rotate env vars, env groups, and secret files on a running Render service without leaking values or deleting keys by accident.

## When to Use

- A deploy failed or the app crashed because a key is missing or wrong (often handed off from [deploy status](deploy-status-and-build-failures.md)).
- Add, change, or rotate one var or secret file, or replace the whole set.
- Create, link, or unlink an env group.
- Check that `render.yaml` and the live service agree.

## Inputs

- Workspace (`render workspace current`) and service ID `srv-...` (`render services -o json`).
- `RENDER_API_KEY` exported in the shell (needed for every REST call below).
- The key names to change. Ask the user to supply new values through a prompt or file, never pasted into chat.

## Workflow

### 1. Pick the change path

The Render CLI cannot list or change env vars on an existing service. It only sets them at creation (`render services create --env-var KEY=VALUE --secret-file NAME:LOCAL_PATH`). Use one of these instead:

| Path | Scope | Deploy behavior |
|---|---|---|
| Dashboard, service Environment page | Vars, secret files, group links | Three save modes: "Save, rebuild, and deploy", "Save and deploy" (reuses the build), "Save only" (applies on the next deploy). Saving a secret file or linking a group triggers a deploy. |
| Render MCP `update_environment_variables` | Service vars only | Merges by default (`replace: false`); `replace: true` replaces every var. **Triggers a deploy automatically.** |
| REST `PUT /services/{id}/env-vars/{key}` | One var | Expected not to deploy, like the collection `PUT` (unverified for the per-key endpoint). Confirm with `render deploys list` afterwards. |
| REST `PUT /services/{id}/env-vars` | All vars | Does not deploy. **Deletes every key you omit.** |

Prefer the REST per-key `PUT` when you want to control when the deploy happens, and MCP when one merge-plus-deploy is what the user wants.

### 2. Inspect keys, never values

```bash
SRV=srv-xxxxx
API=https://api.render.com/v1
AUTH="Authorization: Bearer $RENDER_API_KEY"

# Keys only
curl -fsS -H "$AUTH" "$API/services/$SRV/env-vars?limit=100" | jq -r '.[].envVar.key' | sort

# Keys with masked values, only when you must compare
curl -fsS -H "$AUTH" "$API/services/$SRV/env-vars?limit=100" | jq -r '.[].envVar
  | .key + "=" + (if (.value | length) > 12 then .value[0:3] + "…" + .value[-3:] else "****" end)'
```

The response is a paginated list of `{envVar: {key, value}, cursor}`. If there are more than 100 keys, pass the last item's `cursor` as `&cursor=...`. If the jq output is empty or errors, inspect the raw shape first with `jq 'map(keys)'` (it prints no values) and adjust the filter.

Linked env groups and secret files (names only):

```bash
# All env groups in the workspace, with the services each one is linked to
curl -fsS -H "$AUTH" "$API/env-groups?limit=100" \
  | jq -r '.[].envGroup | .id + "  " + .name + "  " + ([.serviceLinks[]?.id] | join(","))'

# Secret file names on the service
curl -fsS -H "$AUTH" "$API/services/$SRV/secret-files" | jq -r '.[].secretFile.name'
```

The `serviceLinks` field and the `secretFile.name` shape are unverified. Run `jq 'map(keys)'` on the raw output first if these filters print nothing.

### 3. Change one var safely (requires user approval)

State the workspace, service ID, and key, then wait for approval. Read the value without echoing it, so it never reaches shell history or the transcript:

```bash
KEY=STRIPE_SECRET_KEY
read -rs NEW_VALUE            # user types or pastes; nothing is echoed
jq -n --arg v "$NEW_VALUE" '{value: $v}' \
  | curl -fsS -X PUT -H "$AUTH" -H "Content-Type: application/json" \
      --data @- "$API/services/$SRV/env-vars/$KEY" | jq -r '.key'
unset NEW_VALUE
```

To have Render generate a random value, send `{"generateValue": true}` instead. To delete a key, use `curl -fsS -X DELETE -H "$AUTH" "$API/services/$SRV/env-vars/$KEY"`.

MCP alternative: `update_environment_variables` with `serviceId`, `envVars: [{key, value}]`, and `replace: false`. Tell the user it will start a deploy.

### 4. Apply the change (requires user approval)

REST changes sit unapplied until a deploy. **`render restart` does not pick up new env values.** It reuses the last deploy's config.

```bash
render deploys create "$SRV" --wait -o text            # reuses code, picks up new env
render deploys list "$SRV" -o json | jq -r 'map(.deploy // .) | sort_by(.createdAt) | last | .id + " " + .status'
```

If the var is read at build time (asset compilation, Docker `ARG`), add `--clear-cache` only when stale cached output is suspected. On failure, go to [deploy status and build failures](deploy-status-and-build-failures.md).

### 5. Bulk replace (requires user approval)

`PUT /services/{id}/env-vars` replaces the whole set. Any key missing from the body is deleted.

```bash
BK=$(mktemp -d "$HOME/.render-env-XXXX")   # outside the repo
chmod 700 "$BK"
curl -fsS -H "$AUTH" "$API/services/$SRV/env-vars?limit=100" \
  | jq '[.[].envVar | {key, value}]' > "$BK/current.json"
chmod 600 "$BK/current.json"

# Build new.json from current.json, e.g. drop one key and set another from stdin
read -rs NEW_VALUE
jq --arg v "$NEW_VALUE" 'map(select(.key != "OLD_FLAG")) + [{key: "NEW_FLAG", value: $v}]
  | unique_by(.key)' "$BK/current.json" > "$BK/new.json"
chmod 600 "$BK/new.json"; unset NEW_VALUE

# Key-level diff to show the user (no values)
diff <(jq -r '.[].key' "$BK/current.json" | sort) <(jq -r '.[].key' "$BK/new.json" | sort)
```

Show the diff, list every removed key by name, and get explicit approval. Then:

```bash
curl -fsS -X PUT -H "$AUTH" -H "Content-Type: application/json" \
  --data @"$BK/new.json" "$API/services/$SRV/env-vars" | jq -r '.[].envVar.key' | sort
rm -rf "$BK"
```

Re-run step 2, confirm the key list matches `new.json`, delete the backup, then deploy (step 4).

### 6. Env groups (requires user approval for every mutation)

```bash
# Link and unlink a group (dashboard linking triggers a deploy; assume the API call does not)
curl -fsS -X POST   -H "$AUTH" "$API/env-groups/$GROUP_ID/services/$SRV"
curl -fsS -X DELETE -H "$AUTH" "$API/env-groups/$GROUP_ID/services/$SRV"
# Set one key in a group (same stdin pattern as step 3)
jq -n --arg v "$NEW_VALUE" '{value: $v}' | curl -fsS -X PUT -H "$AUTH" \
  -H "Content-Type: application/json" --data @- "$API/env-groups/$GROUP_ID/env-vars/$KEY"
```

Create a group with `POST /env-groups` (request body fields unverified; prefer the dashboard or a Blueprint `envVarGroups` entry).

- **Precedence:** a key set on the service always wins over the same key in a linked group (guaranteed). Between two linked groups with the same key, precedence is not guaranteed. Avoid collisions.
- A group change affects every linked service. List them (step 2) before editing.
- **Rollbacks do not restore env group values.** They restore the service's own env vars but keep current group values, so fix a bad group value forward.

### 7. Secret files

- Mounted at `/etc/secrets/<name>`; native (non-Docker) services also get a copy in the repo root.
- Not readable in a Docker build as plain files. Use a BuildKit secret mount (`RUN --mount=type=secret,id=<name>,dst=/etc/secrets/<name> ...`). Group secret files are included.
- Manage via `GET|PUT|DELETE /services/{id}/secret-files/{name}` or the dashboard (a dashboard save triggers a deploy). Never `cat` one during an investigation; check existence with `test -f` in `render ssh`.

### 8. Audit drift between render.yaml and the live service

```bash
yq -r '.services[] | select(.name == "my-app") | .envVars[] | select(has("key")) | .key' render.yaml | sort > /tmp/yaml-keys
curl -fsS -H "$AUTH" "$API/services/$SRV/env-vars?limit=100" | jq -r '.[].envVar.key' | sort > /tmp/live-keys
comm -3 /tmp/yaml-keys /tmp/live-keys   # col 1: only in yaml, col 2: only live
rm /tmp/yaml-keys /tmp/live-keys
```

Keys that exist only live are not removed by a Blueprint sync. Either add them to `render.yaml` (with `sync: false` for secrets) or delete them with user approval. `fromGroup` entries have no `key`, so compare group keys separately. Validate any edit with `render blueprints validate render.yaml`.

### 9. Rotate a secret (requires user approval)

1. Create the new credential at the provider and keep the old one valid.
2. Set the new value (step 3) and deploy with `--wait` (step 4).
3. Verify: the deploy is `live`, the health check passes, and `render logs -r "$SRV" --level error --start 15m --limit 50 -o text` shows no auth errors.
4. Only then revoke the old credential at the provider.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---|---|---|
| Changed a var, app still sees the old value | REST `PUT` or "Save only" does not deploy; `render restart` reuses old config | `render deploys create <srv> --wait` |
| Unexpected deploy started after an env edit | MCP `update_environment_variables`, dashboard save-and-deploy, or a group link | Expected; watch it with [deploy status](deploy-status-and-build-failures.md) |
| Keys vanished after an update | Collection `PUT` or MCP `replace: true` omitted them | Restore from the backup with a per-key `PUT`, then deploy |
| Service value ignored, group value expected | Service-level key overrides the group | Delete the service-level key, or set it there |
| Bad group value persists after rollback | Rollbacks keep current group values | Fix the group value, then deploy |
| `KeyError` / `Missing secret_key_base` at boot | `RAILS_MASTER_KEY` or `SECRET_KEY_BASE` missing | Set it (step 3), deploy |
| Docker build cannot read a secret file | Secret files are not plain files at build time | BuildKit secret mount (step 7) |
| `sync: false` key empty on an existing service | Prompt only fires on initial Blueprint creation | Set it via dashboard or step 3 |

## Rails Notes

- `RAILS_MASTER_KEY` holds the contents of `config/master.key`. Without it, credentials fail to decrypt at boot or during `assets:precompile`.
- All env values are strings. Cast them: `ENV.fetch("WEB_CONCURRENCY", 2).to_i`, and compare booleans to `"true"`.
- Docker services receive env vars as build args, so declare `ARG RAILS_MASTER_KEY` only if the build needs it, and prefer a secret mount for real secrets. Native Ruby builds see service env vars during the build (unverified).
- Set `WEB_CONCURRENCY` explicitly so small instances do not get OOM-killed (see [logs](logs.md)).

Full Blueprint example for a Rails web service:

```yaml
services:
  - type: web
    name: my-app
    runtime: ruby
    buildCommand: ./bin/render-build.sh
    preDeployCommand: bundle exec rails db:migrate
    startCommand: bundle exec puma -C config/puma.rb
    healthCheckPath: /up
    envVars:
      - key: RAILS_MASTER_KEY
        sync: false                  # prompted only when the Blueprint is first created
      - key: SECRET_KEY_BASE
        generateValue: true          # generated only if not already set
      - key: DATABASE_URL
        fromDatabase:
          name: my-app-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: my-app-redis
          type: keyvalue
          property: connectionString
      - key: WEB_CONCURRENCY
        value: "2"
      - key: APP_HOST
        value: app.example.com
        previewValue: preview.example.com
      - fromGroup: my-app-shared
envVarGroups:
  - name: my-app-shared
    envVars:                         # value or generateValue only; no sync:false or references
      - key: RAILS_LOG_LEVEL
        value: info
```

Gotchas: `sync: false` values are not copied to preview environments, and Blueprint syncs never delete vars omitted from the file.

## Done When

- [ ] Workspace and service ID were stated, and the user approved every mutation.
- [ ] Step 2 key list shows the expected keys; no values were printed.
- [ ] A deploy that includes the change is `live` (`render deploys list <srv> -o json`).
- [ ] No new errors in `render logs -r <srv> --level error --limit 50 -o text`.
- [ ] Backup files are deleted, and no secrets were committed or added to `render.yaml`.
- [ ] `render blueprints validate` passes if `render.yaml` changed; drift (step 8) is resolved or reported.
- [ ] For a rotation, the old credential was revoked only after verification.

## Related

- [Deployment status and build failures](deploy-status-and-build-failures.md)
- [Application and infrastructure logs](logs.md)
- [Failed deployment recovery](failed-deploy-recovery.md)
