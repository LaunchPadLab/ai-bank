#!/usr/bin/env python3
"""Guarded remediation for known Render infrastructure issues.

Two subcommands:

  plan   Read-only. Fetch service state, run the detectors, and write a
         reviewable plan (plan.json + plan.md). Exits 2 when an issue is found.
  apply  Execute a previously generated plan after re-checking every guard:
         plan age, typed service confirmation, action allowlist, state
         fingerprint, and no deploy in progress. Verifies the result.

Known issues handled:

  oom-crash-loop   Repeated OOM kills. Lower WEB_CONCURRENCY by one step and
                   redeploy (REST env changes do not deploy on their own).
  bad-live-deploy  The newest live deploy is crash-looping and an earlier
                   deploy exists. Disable auto-deploy, then roll back.

Standard library only. Requires RENDER_API_KEY.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True

PLAN_VERSION = 1
PLAN_TTL = timedelta(minutes=30)
DEFAULT_BASE_URL = "https://api.render.com/v1"
DEFAULT_STATE_DIR = Path.home() / ".render-remediation"
PAGE_SIZE = 100
MAX_PAGES = 10

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_PLAN = 2
EXIT_REFUSED = 3
EXIT_VERIFY_FAILED = 4

IN_PROGRESS_STATUSES = frozenset(
    {"created", "queued", "build_in_progress", "pre_deploy_in_progress", "update_in_progress"}
)
FAILED_STATUSES = frozenset({"build_failed", "pre_deploy_failed", "update_failed", "canceled"})
REMEDIABLE_SERVICE_TYPES = frozenset({"web_service", "private_service", "background_worker"})

CONCURRENCY_KEY = "WEB_CONCURRENCY"
OOM_MIN_EVENTS = 2
CRASH_MIN_EVENTS = 3
DEPLOY_TIMEOUT = timedelta(minutes=20)
DEPLOY_POLL_SECONDS = 15

# Instance RAM by plan, for both legacy names and current plan IDs.
PLAN_MEMORY_MB = {
    "free": 512,
    "starter": 512,
    "standard": 2048,
    "pro": 4096,
    "pro_plus": 8192,
    "pro_max": 16384,
    "pro_ultra": 32768,
}
PLAN_ID_RE = re.compile(r"^\d+(?:\.\d+)?c-(\d+)(mb|g)$")


class GuardError(Exception):
    """A guard refused to apply a plan."""


class RenderAPIError(Exception):
    def __init__(self, status, message):
        super().__init__(f"Render API {status}: {message}")
        self.status = status
        self.message = message


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


class RenderClient:
    def __init__(self, api_key, base_url=DEFAULT_BASE_URL, max_retries=4, sleep=time.sleep):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._sleep = sleep

    def request(self, method, path, query=None, body=None):
        """Return ``(status, payload)``. ``payload`` is None for an empty body."""
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    return resp.status, json.loads(raw) if raw.strip() else None
            except urllib.error.HTTPError as err:
                raw = err.read()
                if err.code == 429 and attempt < self.max_retries:
                    retry_after = err.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    self._sleep(delay + random.uniform(0, 1))
                    continue
                raise RenderAPIError(err.code, _error_message(raw, err.reason)) from None
        raise RenderAPIError(429, "rate limited; retries exhausted")


def _error_message(raw, fallback):
    try:
        return json.loads(raw).get("message") or str(fallback)
    except (ValueError, AttributeError):
        return str(fallback)


def paginate(client, path, key, query=None):
    """Collect a cursor-paginated list, unwrapping ``[{key: {...}, cursor}]``."""
    params = dict(query or {})
    params["limit"] = PAGE_SIZE
    items = []
    for _ in range(MAX_PAGES):
        _, page = client.request("GET", path, params)
        if not page:
            break
        items.extend(entry.get(key, entry) for entry in page)
        cursor = page[-1].get("cursor")
        if not cursor or len(page) < PAGE_SIZE:
            break
        params["cursor"] = cursor
    return items


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value):
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    # Python 3.10 only accepts 3- or 6-digit fractions.
    match = re.match(r"^(.*T\d\d:\d\d:\d\d)\.(\d+)(.*)$", text)
    if match:
        head, frac, tail = match.groups()
        text = f"{head}.{frac[:6].ljust(6, '0')}{tail}"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_window(value):
    match = re.fullmatch(r"(\d+)([mhd])", value.strip())
    if not match:
        raise argparse.ArgumentTypeError("use a duration like 30m, 2h, or 1d")
    units = {"m": "minutes", "h": "hours", "d": "days"}
    return timedelta(**{units[match.group(2)]: int(match.group(1))})


# ---------------------------------------------------------------------------
# State collection (read-only)
# ---------------------------------------------------------------------------


def fetch_state(client, service_id, window, now, include_metrics=True):
    _, service = client.request("GET", f"/services/{service_id}")
    deploys = paginate(
        client,
        f"/services/{service_id}/deploys",
        "deploy",
        {"createdAfter": iso(now - max(window, timedelta(days=30)))},
    )
    deploys.sort(key=lambda d: d.get("createdAt") or "")
    failures = paginate(
        client,
        f"/services/{service_id}/events",
        "event",
        {"startTime": iso(now - window), "endTime": iso(now), "type": "server_failed"},
    )
    failures.sort(key=lambda e: e.get("timestamp") or "")
    return {
        "service": service,
        "deploys": deploys,
        "failures": failures,
        "web_concurrency": read_web_concurrency(client, service_id),
        "memory": fetch_memory(client, service_id, window, now) if include_metrics else None,
    }


def read_web_concurrency(client, service_id):
    """Read only the WEB_CONCURRENCY key. No other env value is ever fetched."""
    try:
        _, env_var = client.request("GET", f"/services/{service_id}/env-vars/{CONCURRENCY_KEY}")
    except RenderAPIError as err:
        if err.status == 404:
            return None
        raise
    return (env_var or {}).get("value")


def fetch_memory(client, service_id, window, now):
    """Best-effort peak memory vs limit. Returns None if metrics are unavailable."""
    query = {
        "resource": service_id,
        "startTime": iso(now - window),
        "endTime": iso(now),
        "resolutionSeconds": 300,
    }
    try:
        _, usage = client.request("GET", "/metrics/memory", query)
        _, limit = client.request("GET", "/metrics/memory-limit", query)
    except (RenderAPIError, urllib.error.URLError):
        return None
    peak, unit = _series_max(usage)
    cap, _ = _series_max(limit)
    if peak is None:
        return None
    result = {"peak": peak, "limit": cap, "unit": unit}
    if cap:
        result["peakPercentOfLimit"] = round(100 * peak / cap, 1)
    return result


def _series_max(series):
    values = [v.get("value") for s in series or [] for v in s.get("values", [])]
    values = [v for v in values if isinstance(v, (int, float))]
    unit = (series or [{}])[0].get("unit") if series else None
    return (max(values) if values else None), unit


# ---------------------------------------------------------------------------
# Detectors (pure functions over fetched state)
# ---------------------------------------------------------------------------


def _reason(event):
    return ((event.get("details") or {}).get("reason")) or {}


def oom_events(events):
    return [e for e in events if _reason(e).get("oomKilled")]


def crash_events(events):
    """Non-OOM process failures: crashes, failed health checks, early exits, timeouts."""
    crash_keys = ("nonZeroExit", "unhealthy", "earlyExit", "timedOutReason", "timedOutSeconds")
    return [
        e
        for e in events
        if not _reason(e).get("oomKilled")
        and any(_reason(e).get(k) is not None for k in crash_keys)
    ]


def plan_memory_mb(plan):
    if not plan:
        return None
    if plan in PLAN_MEMORY_MB:
        return PLAN_MEMORY_MB[plan]
    match = PLAN_ID_RE.match(plan)
    if not match:
        return None
    amount, unit = int(match.group(1)), match.group(2)
    return amount if unit == "mb" else amount * 1024


def _int_or_none(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def detect_oom_crash_loop(state, now, window):
    service = state["service"]
    if service.get("type") not in REMEDIABLE_SERVICE_TYPES:
        return None
    ooms = oom_events(state["failures"])
    if len(ooms) < OOM_MIN_EVENTS:
        return None

    sid = service["id"]
    plan_name = (service.get("serviceDetails") or {}).get("plan")
    memory_mb = plan_memory_mb(plan_name)
    raw_current = state["web_concurrency"]
    current = _int_or_none(raw_current)

    evidence = {
        "oomKilledEvents": len(ooms),
        "firstAt": ooms[0].get("timestamp"),
        "lastAt": ooms[-1].get("timestamp"),
        "eventIds": [e.get("id") for e in ooms][:20],
        "memoryLimit": _reason(ooms[-1])["oomKilled"].get("memoryLimit"),
        "plan": plan_name,
        "planMemoryMB": memory_mb,
        CONCURRENCY_KEY: raw_current if raw_current is not None else "(unset)",
    }
    if state.get("memory"):
        evidence["memoryMetrics"] = state["memory"]

    risks = [
        "Fewer Puma workers lowers peak memory but also lowers request throughput.",
        "Only takes effect if config/puma.rb reads WEB_CONCURRENCY for its worker count.",
    ]
    newest = _newest_live(state["deploys"])
    first_oom = parse_time(ooms[0].get("timestamp"))
    if (
        newest
        and first_oom
        and parse_time(newest.get("finishedAt") or "")
        and (first_oom >= parse_time(newest["finishedAt"]))
    ):
        risks.append(
            f"The OOM kills started after deploy {newest['id']} went live. If that release "
            "introduced a memory regression, rolling it back may be the better fix."
        )

    if current is not None and current <= 1:
        return _finding(
            "oom-crash-loop",
            f"{len(ooms)} OOM kills in the last {_fmt(window)}, and {CONCURRENCY_KEY} is "
            f"already {current}. There is no safe automatic step left.",
            evidence,
            actions=[],
            manual=[
                "Move the service to a plan with more memory (dashboard, Settings, Instance Type).",
                "Or lower memory per process: reduce RAILS_MAX_THREADS, enable jemalloc, "
                "or find the leak with the memory metrics and app logs.",
            ],
            risks=risks,
            revert=[],
        )
    if current is None and raw_current not in (None, ""):
        return _finding(
            "oom-crash-loop",
            f"{len(ooms)} OOM kills, but {CONCURRENCY_KEY} has a non-integer value, so the "
            "script will not change it.",
            evidence,
            actions=[],
            manual=[f"Set {CONCURRENCY_KEY} to an explicit integer, then re-run `plan`."],
            risks=risks,
            revert=[],
        )

    if current is None:
        target = 1 if memory_mb is None or memory_mb <= 1024 else 2
        why = (
            f"{CONCURRENCY_KEY} is unset, so Rails derives workers from the host CPU count. "
            f"Pin it to {target} for a {memory_mb or 'unknown'} MB instance."
        )
        revert = [
            f"Remove the key again: `DELETE /services/{sid}/env-vars/{CONCURRENCY_KEY}` "
            "(or delete it in the dashboard), then deploy."
        ]
    else:
        target = current - 1
        why = f"Lower {CONCURRENCY_KEY} from {current} to {target}."
        revert = [
            f"Set {CONCURRENCY_KEY} back to {current}: "
            f"`PUT /services/{sid}/env-vars/{CONCURRENCY_KEY}` with "
            f'`{{"value": "{current}"}}`, then `render deploys create {sid} --wait`.'
        ]

    return _finding(
        "oom-crash-loop",
        f"{len(ooms)} OOM kills in the last {_fmt(window)}. {why}",
        evidence,
        actions=[
            _action(
                "set_env_var",
                {"key": CONCURRENCY_KEY, "value": str(target)},
                f"Set {CONCURRENCY_KEY}={target} (does not deploy on its own).",
                f"Dashboard: Environment, set {CONCURRENCY_KEY}={target}, Save only.",
            ),
            _action(
                "trigger_deploy",
                {"clearCache": "do_not_clear"},
                "Deploy so the new value takes effect. `render restart` would not pick it up.",
                f"render deploys create {sid} --wait",
            ),
        ],
        manual=[],
        risks=risks,
        revert=revert,
        checklist=[f"config/puma.rb sets `workers` from ENV['{CONCURRENCY_KEY}']."],
        verify_mode="no_oom",
    )


def detect_bad_live_deploy(state, now, window):
    service = state["service"]
    deploys = state["deploys"]
    if service.get("type") not in REMEDIABLE_SERVICE_TYPES or not deploys:
        return None
    newest = deploys[-1]
    finished = parse_time(newest.get("finishedAt") or "")
    if newest.get("status") != "live" or not finished or finished < now - window:
        return None
    crashes = [
        e
        for e in crash_events(state["failures"])
        if (parse_time(e.get("timestamp") or "") or finished) >= finished
    ]
    if len(crashes) < CRASH_MIN_EVENTS:
        return None
    target = next((d for d in reversed(deploys[:-1]) if d.get("status") == "deactivated"), None)

    sid = service["id"]
    evidence = {
        "liveDeploy": _deploy_summary(newest),
        "failuresSinceLive": len(crashes),
        "eventIds": [e.get("id") for e in crashes][:20],
        "reasons": sorted(
            {k for e in crashes for k, v in _reason(e).items() if v not in (None, False)}
        ),
        "rollbackTarget": _deploy_summary(target) if target else None,
        "autoDeploy": service.get("autoDeploy"),
    }
    risks = [
        "A rollback does not revert database migrations. If this release ran a destructive "
        "migration, the old code may fail against the new schema. Fix forward instead.",
        "The service's own env vars revert to their values at the target deploy. "
        "Env group values stay as they are now.",
        "Only deploys whose build artifacts Render still retains can be rolled back to.",
    ]
    manual = []
    if not target:
        manual.append("No earlier deactivated deploy to roll back to. Fix forward.")
    if newest.get("trigger") == "rollback":
        manual.append(
            "The live deploy is itself a rollback. Not rolling back again automatically; "
            "investigate with the logs workflow."
        )
    if manual:
        return _finding(
            "bad-live-deploy",
            f"Deploy {newest['id']} is live and has {len(crashes)} failures, but no safe "
            "automatic rollback is available.",
            evidence,
            actions=[],
            manual=manual,
            risks=risks,
            revert=[],
        )

    actions = []
    if service.get("autoDeploy") == "yes":
        actions.append(
            _action(
                "patch_auto_deploy",
                {"autoDeploy": "no"},
                "Turn off auto-deploy first. An API rollback leaves it on, so the next push "
                "would re-ship the bad commit.",
                f"render services update {sid} --auto-deploy=false",
            )
        )
    actions.append(
        _action(
            "rollback",
            {"deployId": target["id"]},
            f"Roll back to {target['id']} ({_short_commit(target)}). Reuses that build artifact.",
            "Dashboard: Deploys, Rollback on the target deploy (this also disables auto-deploy).",
        )
    )
    return _finding(
        "bad-live-deploy",
        f"Deploy {newest['id']} ({_short_commit(newest)}) went live and has failed "
        f"{len(crashes)} times since. Roll back to {target['id']} ({_short_commit(target)}).",
        evidence,
        actions=actions,
        manual=[],
        risks=risks,
        revert=[
            "Re-enable auto-deploy once the fix is merged: "
            f"`render services update {sid} --auto-deploy=true`.",
            f"To undo the rollback, roll forward to {newest['id']} with the same rollback "
            "endpoint, or deploy a fixed commit.",
        ],
        checklist=["No destructive migration shipped in the bad release."],
        verify_mode="no_failures",
    )


DETECTORS = (detect_oom_crash_loop, detect_bad_live_deploy)


def detect(state, now, window):
    for detector in DETECTORS:
        finding = detector(state, now, window)
        if finding:
            return finding
    return None


def _finding(
    detector, summary, evidence, actions, manual, risks, revert, checklist=(), verify_mode=None
):
    return {
        "detector": detector,
        "summary": summary,
        "evidence": evidence,
        "actions": actions,
        "manualSteps": manual,
        "risks": risks,
        "revert": revert,
        "checklist": list(checklist),
        "verify": {"mode": verify_mode} if verify_mode else None,
    }


def _action(kind, params, description, equivalent):
    return {"kind": kind, "params": params, "description": description, "equivalent": equivalent}


def _newest_live(deploys):
    return next((d for d in reversed(deploys) if d.get("status") == "live"), None)


def _short_commit(deploy):
    commit = (deploy or {}).get("commit") or {}
    sha = (commit.get("id") or "")[:7]
    return sha or ((deploy or {}).get("image") or {}).get("ref") or "no commit"


def _deploy_summary(deploy):
    commit = deploy.get("commit") or {}
    return {
        "id": deploy.get("id"),
        "status": deploy.get("status"),
        "trigger": deploy.get("trigger"),
        "commit": _short_commit(deploy),
        "message": (commit.get("message") or "").splitlines()[0][:80]
        if commit.get("message")
        else "",
        "finishedAt": deploy.get("finishedAt"),
    }


def _fmt(window):
    minutes = int(window.total_seconds() // 60)
    if minutes % 1440 == 0:
        return f"{minutes // 1440}d"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


# ---------------------------------------------------------------------------
# Plan artifact
# ---------------------------------------------------------------------------


def fingerprint(state):
    service = state["service"]
    newest = state["deploys"][-1] if state["deploys"] else {}
    fields = {
        "latestDeployId": newest.get("id"),
        "latestDeployStatus": newest.get("status"),
        "autoDeploy": service.get("autoDeploy"),
        "suspended": service.get("suspended"),
        CONCURRENCY_KEY: state["web_concurrency"],
    }
    digest = hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()
    return {"fields": fields, "sha256": digest}


def build_plan(state, finding, now, window):
    service = state["service"]
    return {
        "version": PLAN_VERSION,
        "createdAt": iso(now),
        "expiresAt": iso(now + PLAN_TTL),
        "windowMinutes": int(window.total_seconds() // 60),
        "service": {
            "id": service["id"],
            "name": service.get("name"),
            "type": service.get("type"),
            "plan": (service.get("serviceDetails") or {}).get("plan"),
            "ownerId": service.get("ownerId"),
            "dashboardUrl": service.get("dashboardUrl"),
        },
        **finding,
        "fingerprint": fingerprint(state),
    }


def build_request(kind, service_id, params):
    """Map an allowlisted action to its HTTP request. The plan never carries raw paths."""
    if kind == "patch_auto_deploy":
        return "PATCH", f"/services/{service_id}", {"autoDeploy": params["autoDeploy"]}
    if kind == "rollback":
        return "POST", f"/services/{service_id}/rollback", {"deployId": params["deployId"]}
    if kind == "set_env_var":
        return (
            "PUT",
            f"/services/{service_id}/env-vars/{params['key']}",
            {"value": params["value"]},
        )
    if kind == "trigger_deploy":
        return "POST", f"/services/{service_id}/deploys", {"clearCache": params["clearCache"]}
    raise GuardError(f"action kind {kind!r} is not allowed")


def validate_action(action):
    kind = action.get("kind")
    params = action.get("params")
    if not isinstance(params, dict):
        raise GuardError(f"action {kind!r} parameters must be a JSON object")
    if kind == "patch_auto_deploy":
        ok = params == {"autoDeploy": "no"} or params == {"autoDeploy": "yes"}
    elif kind == "rollback":
        ok = set(params) == {"deployId"} and re.fullmatch(r"dep-[a-z0-9]+", str(params["deployId"]))
    elif kind == "set_env_var":
        value = str(params.get("value", ""))
        ok = (
            set(params) == {"key", "value"}
            and params["key"] == CONCURRENCY_KEY
            and re.fullmatch(r"[0-9]+", value)
            and 1 <= int(value) <= 32
        )
    elif kind == "trigger_deploy":
        ok = params in ({"clearCache": "do_not_clear"}, {"clearCache": "clear"})
    else:
        raise GuardError(f"action kind {kind!r} is not in the allowlist")
    if not ok:
        raise GuardError(f"action {kind!r} has parameters outside the allowlist: {params}")


def render_markdown(plan, plan_path):
    service = plan["service"]
    sid = service["id"]
    lines = [
        f"# Render remediation plan: {service.get('name') or sid}",
        "",
        f"- **Service:** `{sid}` ({service.get('type')}, plan `{service.get('plan')}`)",
        f"- **Workspace (owner):** `{service.get('ownerId')}`",
        f"- **Detector:** `{plan['detector']}`",
        f"- **Created:** {plan['createdAt']}. **Expires:** {plan['expiresAt']}.",
        "",
        "## Summary",
        "",
        plan["summary"],
        "",
        "## Evidence",
        "",
        "| Field | Value |",
        "|---|---|",
    ]
    for key, value in plan["evidence"].items():
        shown = json.dumps(value) if isinstance(value, (dict, list)) else value
        lines.append(f"| {key} | `{shown}` |")

    lines += ["", "## Proposed Actions", ""]
    if plan["actions"]:
        lines.append("Run in this order. Each one changes production.")
        lines.append("")
        for index, action in enumerate(plan["actions"], 1):
            method, path, body = build_request(action["kind"], sid, action["params"])
            lines += [
                f"{index}. **{action['kind']}**: {action['description']}",
                f"   - API: `{method} {path}` with `{json.dumps(body)}`",
                f"   - Equivalent: {action['equivalent']}",
            ]
    else:
        lines.append("None. No safe automatic action exists; `apply` will refuse this plan.")
    if plan["manualSteps"]:
        lines += ["", "## Manual Steps", ""]
        lines += [f"- {step}" for step in plan["manualSteps"]]

    lines += ["", "## Risks", ""]
    lines += [f"- {risk}" for risk in plan["risks"]]
    if plan["checklist"]:
        lines += ["", "## Reviewer Checklist", ""]
        lines += [f"- [ ] {item}" for item in plan["checklist"]]
    if plan["revert"]:
        lines += ["", "## How to Revert", ""]
        lines += [f"- {step}" for step in plan["revert"]]

    lines += [
        "",
        "## Apply",
        "",
        "Only after the user has reviewed and approved this plan:",
        "",
        "```bash",
        f"python3 render_remediate.py apply --plan {plan_path} --confirm {sid} --dry-run",
        f"python3 render_remediate.py apply --plan {plan_path} --confirm {sid}",
        "```",
        "",
        "`apply` refuses if the plan expired, the confirmation does not match, the service "
        "changed since this plan was made, or a deploy is in progress.",
        "",
    ]
    return "\n".join(lines)


def write_plan(plan, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "plan.json"
    json_path.write_text(json.dumps(plan, indent=2) + "\n")
    (out_dir / "plan.md").write_text(render_markdown(plan, json_path))
    return json_path


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def check_plan(plan, confirm, now):
    if not isinstance(plan, dict):
        raise GuardError("plan file is not a JSON object")
    if plan.get("version") != PLAN_VERSION:
        raise GuardError(f"unsupported plan version {plan.get('version')!r}")
    expires = parse_time(plan.get("expiresAt") or "")
    if not expires or now > expires:
        raise GuardError(f"plan expired at {plan.get('expiresAt')}; run `plan` again")
    sid = (plan.get("service") or {}).get("id")
    if not sid or not re.fullmatch(r"srv-[a-z0-9]+", sid):
        raise GuardError("plan has no valid service ID")
    if confirm != sid:
        raise GuardError(f"--confirm {confirm!r} does not match the plan's service {sid}")
    fingerprint_ = plan.get("fingerprint")
    if not isinstance(fingerprint_, dict) or not isinstance(fingerprint_.get("fields"), dict):
        raise GuardError("plan has no state fingerprint")
    actions = plan.get("actions")
    if not actions or not isinstance(actions, list):
        raise GuardError("plan has no automatic actions; follow its manual steps instead")
    for action in actions:
        if not isinstance(action, dict):
            raise GuardError("plan action is not a JSON object")
        validate_action(action)


def check_live_state(plan, state):
    current = fingerprint(state)
    if current["sha256"] != plan["fingerprint"]["sha256"]:
        before, after = plan["fingerprint"]["fields"], current["fields"]
        changed = [k for k in after if before.get(k) != after.get(k)]
        raise GuardError(
            f"service changed since the plan was made ({', '.join(changed)}); run `plan` again"
        )
    newest = state["deploys"][-1] if state["deploys"] else {}
    if newest.get("status") in IN_PROGRESS_STATUSES:
        raise GuardError(
            f"deploy {newest.get('id')} is {newest.get('status')}; wait for it to finish"
        )


def audit(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def apply_plan(client, plan, confirm, *, dry_run, verify_minutes, audit_path, clock, sleep, out):
    now = clock()
    check_plan(plan, confirm, now)
    sid = plan["service"]["id"]
    window = timedelta(minutes=plan.get("windowMinutes", 120))
    check_live_state(plan, fetch_state(client, sid, window, now, include_metrics=False))

    started = clock()
    deploy_id = None
    completed = []
    for action in plan["actions"]:
        method, path, body = build_request(action["kind"], sid, action["params"])
        if dry_run:
            out(f"[dry-run] {method} {path} {json.dumps(body)}")
            continue
        try:
            status, payload = client.request(method, path, body=body)
        except (RenderAPIError, urllib.error.URLError, TimeoutError) as err:
            # A network error may still have reached Render; the summary says "may".
            status = getattr(err, "status", None)
            message = getattr(err, "message", None) or str(err)
            audit(
                audit_path,
                {
                    "at": iso(clock()),
                    "service": sid,
                    "detector": plan["detector"],
                    "action": action["kind"],
                    "request": f"{method} {path}",
                    "status": status,
                    "error": message,
                },
            )
            out(f"{action['kind']}: {method} {path} -> FAILED ({status or 'network'}: {message})")
            if status is None:
                out("The request may or may not have reached Render. Check the dashboard.")
            out(f"Completed before the failure: {', '.join(completed) or 'nothing'}.")
            out("Stopped. Nothing else was sent. Review the plan's revert steps:")
            for step in plan.get("revert") or []:
                out(f"  - {step}")
            return EXIT_ERROR
        completed.append(action["kind"])
        if action["kind"] in ("rollback", "trigger_deploy") and payload:
            deploy_id = payload.get("id") or deploy_id
        audit(
            audit_path,
            {
                "at": iso(clock()),
                "service": sid,
                "detector": plan["detector"],
                "action": action["kind"],
                "request": f"{method} {path}",
                "status": status,
                "deployId": deploy_id,
            },
        )
        out(f"{action['kind']}: {method} {path} -> {status}")
    if dry_run:
        out("Dry run complete. Nothing was sent.")
        return EXIT_OK

    ok, message = verify_result(client, plan, deploy_id, started, verify_minutes, clock, sleep, out)
    audit(
        audit_path,
        {
            "at": iso(clock()),
            "service": sid,
            "verify": "passed" if ok else "failed",
            "detail": message,
        },
    )
    if ok:
        out(f"Verified: {message}")
        return EXIT_OK
    out(f"VERIFICATION FAILED: {message}")
    out("Nothing else was changed. Review the plan's revert steps:")
    for step in plan.get("revert") or []:
        out(f"  - {step}")
    return EXIT_VERIFY_FAILED


def verify_result(client, plan, deploy_id, started, verify_minutes, clock, sleep, out):
    sid = plan["service"]["id"]
    deadline = clock() + DEPLOY_TIMEOUT
    deploy = None
    while True:
        deploys = paginate(
            client,
            f"/services/{sid}/deploys",
            "deploy",
            {"createdAfter": iso(started - timedelta(minutes=1))},
        )
        if deploy_id:
            deploy = next((d for d in deploys if d.get("id") == deploy_id), None)
        else:
            deploy = max(deploys, key=lambda d: d.get("createdAt") or "", default=None)
        status = (deploy or {}).get("status")
        if status == "live":
            break
        if status in FAILED_STATUSES:
            return False, f"deploy {deploy.get('id')} ended {status}"
        if clock() > deadline:
            return (
                False,
                f"deploy {(deploy or {}).get('id')} not live after "
                f"{_fmt(DEPLOY_TIMEOUT)} (status {status})",
            )
        out(
            f"Waiting for deploy {(deploy or {}).get('id') or '(pending)'}: "
            f"{status or 'not created yet'}"
        )
        sleep(DEPLOY_POLL_SECONDS)

    live_at = clock()
    out(f"Deploy {deploy['id']} is live. Watching for failures for {verify_minutes} min.")
    sleep(verify_minutes * 60)
    events = paginate(
        client,
        f"/services/{sid}/events",
        "event",
        {"startTime": iso(live_at), "endTime": iso(clock()), "type": "server_failed"},
    )
    mode = (plan.get("verify") or {}).get("mode")
    bad = oom_events(events) if mode == "no_oom" else events
    if bad:
        return False, f"{len(bad)} server_failed events after deploy {deploy['id']} went live"
    return True, f"deploy {deploy['id']} is live with no new failures for {verify_minutes} min"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_plan(client, args, clock=utcnow, out=print):
    now = clock()
    state = fetch_state(client, args.service, args.window, now)
    finding = detect(state, now, args.window)
    if not finding:
        latest = state["deploys"][-1] if state["deploys"] else {}
        out(
            f"No known issue detected on {args.service} in the last {_fmt(args.window)} "
            f"({len(state['failures'])} server_failed events, "
            f"latest deploy {latest.get('status', 'none')})."
        )
        return EXIT_OK
    plan = build_plan(state, finding, now, args.window)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out or DEFAULT_STATE_DIR / "plans" / f"{args.service}-{stamp}"
    plan_path = write_plan(plan, Path(out_dir))
    out(f"[{plan['detector']}] {plan['summary']}")
    out(f"Plan: {plan_path}")
    out(f"Review: {plan_path.with_suffix('.md')}")
    if not plan["actions"]:
        out("No automatic action available. See the manual steps in the plan.")
    return EXIT_PLAN


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="read-only: detect a known issue and write a plan")
    plan.add_argument("--service", required=True, help="service ID (srv-...)")
    plan.add_argument(
        "--window",
        type=parse_window,
        default=timedelta(hours=2),
        help="lookback, e.g. 30m, 2h (default 2h)",
    )
    plan.add_argument(
        "--out", type=Path, help="output directory (default ~/.render-remediation/plans/...)"
    )

    apply = sub.add_parser("apply", help="execute a reviewed plan, with guards")
    apply.add_argument("--plan", type=Path, required=True, help="path to plan.json")
    apply.add_argument("--confirm", required=True, help="the plan's service ID, typed to confirm")
    apply.add_argument(
        "--dry-run", action="store_true", help="check guards and print requests only"
    )
    apply.add_argument(
        "--verify-minutes",
        type=int,
        default=5,
        help="minutes to watch for failures after live (default 5)",
    )
    apply.add_argument("--audit-log", type=Path, default=DEFAULT_STATE_DIR / "audit.jsonl")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    api_key = os.environ.get("RENDER_API_KEY")
    if not api_key:
        print("RENDER_API_KEY is not set.", file=sys.stderr)
        return EXIT_ERROR
    client = RenderClient(api_key, os.environ.get("RENDER_API_BASE", DEFAULT_BASE_URL))
    try:
        if args.command == "plan":
            return cmd_plan(client, args)
        plan = json.loads(args.plan.read_text())
        return apply_plan(
            client,
            plan,
            args.confirm,
            dry_run=args.dry_run,
            verify_minutes=args.verify_minutes,
            audit_path=args.audit_log,
            clock=utcnow,
            sleep=time.sleep,
            out=print,
        )
    except GuardError as err:
        print(f"REFUSED: {err}", file=sys.stderr)
        return EXIT_REFUSED
    except (RenderAPIError, urllib.error.URLError, OSError, ValueError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
