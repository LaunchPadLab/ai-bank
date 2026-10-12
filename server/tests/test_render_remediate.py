"""Guarded Render remediation script (claude/skills/render-operations/scripts/render_remediate.py).

The script is a standalone stdlib CLI, not a package, so it is loaded by path. A FakeClient stands
in for the Render API; one test drives the real RenderClient against a local HTTP server.
"""

import argparse
import http.server
import importlib.util
import json
import re
import sys
import threading
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.dont_write_bytecode = True  # never leave __pycache__ in the skill dir (validate_all_skills.py rejects it)
SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "claude/skills/render-operations/scripts/render_remediate.py"
)
spec = importlib.util.spec_from_file_location("render_remediate", SCRIPT)
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

NOW = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
WINDOW = timedelta(hours=2)
SID = "srv-abc123"
ENV_PATH = f"/services/{SID}/env-vars/WEB_CONCURRENCY"


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def at(minutes):
    """ISO timestamp ``minutes`` relative to NOW (negative = past)."""
    return rr.iso(NOW + timedelta(minutes=minutes))


def make_service(plan="starter", auto_deploy="yes", type_="web_service"):
    return {
        "id": SID,
        "name": "web",
        "type": type_,
        "autoDeploy": auto_deploy,
        "suspended": "not_suspended",
        "ownerId": "tea-owner1",
        "serviceDetails": {"plan": plan},
    }


def make_deploy(id_, status, created, finished=None, trigger="new_commit"):
    return {
        "id": id_,
        "status": status,
        "trigger": trigger,
        "createdAt": at(created),
        "finishedAt": at(finished) if finished is not None else None,
        "commit": {"id": f"{id_}-sha-0123456", "message": "ship it\nbody"},
    }


def make_event(id_, minutes, **reason):
    return {
        "id": id_,
        "timestamp": at(minutes),
        "type": "server_failed",
        "details": {"reason": reason},
    }


def oom(id_, minutes):
    return make_event(id_, minutes, oomKilled={"memoryLimit": "512Mi"})


def crash(id_, minutes, **reason):
    return make_event(id_, minutes, **(reason or {"nonZeroExit": 1}))


OLD = make_deploy("dep-old1", "deactivated", created=-300, finished=-290)
STALE_LIVE = make_deploy("dep-live1", "live", created=-240, finished=-230)  # outside the window
FRESH_LIVE = make_deploy("dep-new1", "live", created=-40, finished=-30)
OOMS = [oom("evt-o1", -20), oom("evt-o2", -10)]
CRASHES = [
    crash("evt-c1", -25),
    crash("evt-c2", -20, unhealthy="health check failed"),
    crash("evt-c3", -15),
]


def make_state(*, deploys=(), failures=(), concurrency="3", **service_kw):
    return {
        "service": make_service(**service_kw),
        "deploys": list(deploys),
        "failures": list(failures),
        "web_concurrency": concurrency,
        "memory": None,
    }


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self, start=NOW):
        self.now = start
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += timedelta(seconds=seconds)


class FakeClient:
    """Routing-table fake. Values are ``(status, payload)``, an exception, or a callable."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.calls = []

    def request(self, method, path, query=None, body=None):
        # Snapshot the query: paginate() reuses and mutates one params dict across pages.
        self.calls.append((method, path, dict(query) if query else query, body))
        handler = self.routes.get((method, path))
        if handler is None:
            raise AssertionError(f"unexpected request {method} {path}")
        result = handler(query, body) if callable(handler) else handler
        if isinstance(result, Exception):
            raise result
        return result

    @property
    def mutations(self):
        return [(m, p, b) for m, p, _, b in self.calls if m != "GET"]


def make_client(
    clock=None,
    *,
    deploys=(),
    events=(),
    concurrency="3",
    rollout=("queued", "update_in_progress", "live"),
    deploy_response=202,
    **service_kw,
):
    """A stateful fake Render API. Deploys created by apply walk through ``rollout`` per poll."""
    clock = clock or FakeClock()
    client = FakeClient()
    client.service = make_service(**service_kw)
    client.deploys = [dict(d) for d in deploys]
    client.events = list(events)
    client.concurrency = concurrency
    client.pending = {}

    def get_deploys(query, _body):
        for deploy in client.deploys:
            steps = client.pending.get(deploy["id"])
            if steps:
                deploy["status"] = steps.pop(0)
        after = rr.parse_time(query["createdAfter"])
        found = [dict(d) for d in client.deploys if rr.parse_time(d["createdAt"]) >= after]
        found.sort(key=lambda d: d["createdAt"], reverse=True)  # API returns newest first
        return 200, [{"deploy": d, "cursor": f"c{i}"} for i, d in enumerate(found)]

    def get_events(query, _body):
        start, end = rr.parse_time(query["startTime"]), rr.parse_time(query["endTime"])
        hits = [e for e in client.events if start <= rr.parse_time(e["timestamp"]) <= end]
        return 200, [{"event": e, "cursor": f"e{i}"} for i, e in enumerate(hits)]

    def get_env(_query, _body):
        if client.concurrency is None:
            return rr.RenderAPIError(404, "env var not found")
        return 200, {"key": "WEB_CONCURRENCY", "value": client.concurrency}

    def put_env(_query, body):
        client.concurrency = body["value"]
        return 200, {"key": "WEB_CONCURRENCY", "value": body["value"]}

    def new_deploy(id_, trigger):
        deploy = {"id": id_, "status": "created", "trigger": trigger, "createdAt": rr.iso(clock())}
        client.deploys.append(deploy)
        client.pending[id_] = list(rollout)
        return deploy

    def post_deploys(_query, _body):
        deploy = new_deploy("dep-auto1", "api")
        return (202, None) if deploy_response == 202 else (201, dict(deploy))

    def post_rollback(_query, body):
        return 201, dict(new_deploy("dep-rb1", "rollback"))

    def patch_service(_query, body):
        client.service.update(body)
        return 200, dict(client.service)

    series = lambda value: [  # noqa: E731
        {"labels": [{"field": "instance", "value": "i-1"}], "unit": "bytes",
         "values": [{"timestamp": at(-5), "value": value}]}
    ]
    client.routes.update(
        {
            ("GET", f"/services/{SID}"): lambda q, b: (200, dict(client.service)),
            ("GET", f"/services/{SID}/deploys"): get_deploys,
            ("GET", f"/services/{SID}/events"): get_events,
            ("GET", ENV_PATH): get_env,
            ("GET", "/metrics/memory"): (200, series(500_000_000)),
            ("GET", "/metrics/memory-limit"): (200, series(536_870_912)),
            ("PATCH", f"/services/{SID}"): patch_service,
            ("POST", f"/services/{SID}/rollback"): post_rollback,
            ("PUT", ENV_PATH): put_env,
            ("POST", f"/services/{SID}/deploys"): post_deploys,
        }
    )
    return client


def oom_client(clock=None, **kw):
    kw.setdefault("deploys", [OLD, STALE_LIVE])
    kw.setdefault("events", OOMS)
    return make_client(clock, **kw)


def bad_deploy_client(clock=None, **kw):
    kw.setdefault("deploys", [OLD, FRESH_LIVE])
    kw.setdefault("events", CRASHES)
    return make_client(clock, **kw)


def make_plan(client):
    state = rr.fetch_state(client, SID, WINDOW, NOW)
    finding = rr.detect(state, NOW, WINDOW)
    assert finding is not None
    plan = rr.build_plan(state, finding, NOW, WINDOW)
    client.calls.clear()
    return plan


def run_apply(client, plan, clock, tmp_path, *, confirm=SID, dry_run=False):
    lines = []
    code = rr.apply_plan(
        client,
        plan,
        confirm,
        dry_run=dry_run,
        verify_minutes=5,
        audit_path=tmp_path / "audit.jsonl",
        clock=clock,
        sleep=clock.sleep,
        out=lines.append,
    )
    return code, lines


def audit_lines(tmp_path):
    return [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


def test_oom_lowers_web_concurrency_and_redeploys():
    finding = rr.detect(make_state(deploys=[OLD, STALE_LIVE], failures=OOMS), NOW, WINDOW)
    assert finding["detector"] == "oom-crash-loop"
    assert [(a["kind"], a["params"]) for a in finding["actions"]] == [
        ("set_env_var", {"key": "WEB_CONCURRENCY", "value": "2"}),
        ("trigger_deploy", {"clearCache": "do_not_clear"}),
    ]
    assert finding["verify"] == {"mode": "no_oom"}


@pytest.mark.parametrize(
    ("plan", "expected"),
    [("starter", "1"), ("pro", "2"), ("1c-2g", "2"), ("mystery-plan", "1")],
)
def test_oom_with_unset_concurrency_pins_by_plan_memory(plan, expected):
    state = make_state(failures=OOMS, concurrency=None, plan=plan)
    finding = rr.detect_oom_crash_loop(state, NOW, WINDOW)
    assert finding["actions"][0]["params"] == {"key": "WEB_CONCURRENCY", "value": expected}


def test_plan_memory_mb_parses_plan_ids():
    assert rr.plan_memory_mb("1c-2g") == 2048
    assert rr.plan_memory_mb("0.5c-512mb") == 512
    assert rr.plan_memory_mb("mystery-plan") is None


@pytest.mark.parametrize("value", ["1", "auto"])
def test_oom_with_no_safe_step_has_only_manual_steps(value):
    finding = rr.detect_oom_crash_loop(make_state(failures=OOMS, concurrency=value), NOW, WINDOW)
    assert finding["detector"] == "oom-crash-loop"
    assert finding["actions"] == []
    assert finding["manualSteps"]


def test_single_oom_is_not_a_crash_loop():
    assert rr.detect(make_state(failures=OOMS[:1], deploys=[OLD, STALE_LIVE]), NOW, WINDOW) is None


@pytest.mark.parametrize(("auto_deploy", "kinds"), [
    ("yes", ["patch_auto_deploy", "rollback"]),
    ("no", ["rollback"]),
])
def test_bad_live_deploy_rolls_back_to_previous(auto_deploy, kinds):
    state = make_state(deploys=[OLD, FRESH_LIVE], failures=CRASHES, auto_deploy=auto_deploy)
    finding = rr.detect(state, NOW, WINDOW)
    assert finding["detector"] == "bad-live-deploy"
    assert [a["kind"] for a in finding["actions"]] == kinds
    if auto_deploy == "yes":
        assert finding["actions"][0]["params"] == {"autoDeploy": "no"}
    assert finding["actions"][-1]["params"] == {"deployId": "dep-old1"}
    assert finding["verify"] == {"mode": "no_failures"}


def test_bad_live_deploy_without_predecessor_has_no_actions():
    finding = rr.detect(make_state(deploys=[FRESH_LIVE], failures=CRASHES), NOW, WINDOW)
    assert finding["actions"] == [] and finding["manualSteps"]


def test_bad_live_deploy_that_is_a_rollback_is_not_rolled_back_again():
    live = make_deploy("dep-new1", "live", created=-40, finished=-30, trigger="rollback")
    finding = rr.detect(make_state(deploys=[OLD, live], failures=CRASHES), NOW, WINDOW)
    assert finding["actions"] == [] and finding["manualSteps"]


def test_crashes_before_live_do_not_count():
    early = [crash(f"evt-e{i}", -35 - i) for i in range(3)]
    assert rr.detect_bad_live_deploy(make_state(deploys=[OLD, FRESH_LIVE], failures=early),
                                     NOW, WINDOW) is None


def test_live_deploy_outside_window_is_ignored():
    state = make_state(deploys=[OLD, STALE_LIVE], failures=CRASHES)
    assert rr.detect_bad_live_deploy(state, NOW, WINDOW) is None


def test_oom_takes_precedence_over_crashes():
    state = make_state(deploys=[OLD, FRESH_LIVE], failures=CRASHES + OOMS)
    assert rr.detect(state, NOW, WINDOW)["detector"] == "oom-crash-loop"


# ---------------------------------------------------------------------------
# Plan command and artifact
# ---------------------------------------------------------------------------


def plan_args(tmp_path):
    return argparse.Namespace(service=SID, window=WINDOW, out=tmp_path / "p")


def test_cmd_plan_healthy_writes_nothing(tmp_path):
    client = make_client(deploys=[OLD, STALE_LIVE])
    lines = []
    assert rr.cmd_plan(client, plan_args(tmp_path), clock=lambda: NOW, out=lines.append) == rr.EXIT_OK
    assert not (tmp_path / "p").exists()
    assert "No known issue" in lines[0]


def test_cmd_plan_writes_plan_and_never_reads_other_env_vars(tmp_path):
    client = oom_client()
    lines = []
    code = rr.cmd_plan(client, plan_args(tmp_path), clock=lambda: NOW, out=lines.append)
    assert code == rr.EXIT_PLAN
    plan = json.loads((tmp_path / "p/plan.json").read_text())
    markdown = (tmp_path / "p/plan.md").read_text()
    assert plan["detector"] == "oom-crash-loop"
    assert plan["evidence"]["WEB_CONCURRENCY"] == "3"
    assert "| WEB_CONCURRENCY | `3` |" in markdown

    env_paths = [p for _, p, _, _ in client.calls if "/env-vars" in p]
    assert env_paths == [ENV_PATH]
    assert not any(re.search(r"/env-vars$|/env-vars/(?!WEB_CONCURRENCY$)", p)
                   for _, p, _, _ in client.calls)
    assert client.mutations == []


def test_render_markdown_lists_exact_api_requests():
    oom_plan = make_plan(oom_client())
    md = rr.render_markdown(oom_plan, Path("/tmp/plan.json"))
    assert f"API: `PUT /services/{SID}/env-vars/WEB_CONCURRENCY` with `{{\"value\": \"2\"}}`" in md
    assert f"API: `POST /services/{SID}/deploys`" in md

    bad_plan = make_plan(bad_deploy_client())
    md = rr.render_markdown(bad_plan, Path("/tmp/plan.json"))
    assert f"API: `PATCH /services/{SID}` with `{{\"autoDeploy\": \"no\"}}`" in md
    assert f"API: `POST /services/{SID}/rollback` with `{{\"deployId\": \"dep-old1\"}}`" in md


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def refuse(client, plan, tmp_path, match, *, clock=None, confirm=SID):
    with pytest.raises(rr.GuardError, match=match):
        run_apply(client, plan, clock or FakeClock(), tmp_path, confirm=confirm)
    assert client.mutations == []
    assert not (tmp_path / "audit.jsonl").exists()


def test_expired_plan_is_refused(tmp_path):
    client = oom_client()
    plan = make_plan(client)
    refuse(client, plan, tmp_path, "expired", clock=FakeClock(NOW + timedelta(minutes=31)))


def test_confirm_mismatch_is_refused(tmp_path):
    client = oom_client()
    refuse(client, make_plan(client), tmp_path, "does not match", confirm="srv-other")


def test_unsupported_version_is_refused(tmp_path):
    client = oom_client()
    plan = make_plan(client)
    plan["version"] = 2
    refuse(client, plan, tmp_path, "unsupported plan version")


def test_plan_without_actions_is_refused(tmp_path):
    client = oom_client(concurrency="1")
    refuse(client, make_plan(client), tmp_path, "no automatic actions")


@pytest.mark.parametrize("fingerprint", [None, "abc", {"sha256": "x"}, {"fields": []}])
def test_plan_without_valid_fingerprint_is_refused(tmp_path, fingerprint):
    client = oom_client()
    plan = make_plan(client)
    if fingerprint is None:
        del plan["fingerprint"]
    else:
        plan["fingerprint"] = fingerprint
    refuse(client, plan, tmp_path, "fingerprint")
    assert client.calls == []


def test_non_object_plan_and_action_are_refused(tmp_path):
    client = oom_client()
    plan = make_plan(client)
    refuse(client, [plan], tmp_path, "not a JSON object")
    plan["actions"] = ["set_env_var"]
    refuse(client, plan, tmp_path, "not a JSON object")


@pytest.mark.parametrize(
    "action",
    [
        {"kind": "delete_service", "params": {}},
        {"kind": "set_env_var", "params": {"key": "DATABASE_URL", "value": "2"}},
        {"kind": "set_env_var", "params": {"key": "WEB_CONCURRENCY", "value": "0"}},
        {"kind": "set_env_var", "params": {"key": "WEB_CONCURRENCY", "value": "abc"}},
        {"kind": "rollback", "params": {"deployId": "../x"}},
        {"kind": "trigger_deploy", "params": {"clearCache": "do_not_clear", "commitId": "x"}},
    ],
    ids=["unknown-kind", "other-key", "zero", "non-integer", "path-traversal", "extra-param"],
)
def test_tampered_actions_are_refused(tmp_path, action):
    client = oom_client()
    plan = make_plan(client)
    plan["actions"][0] = {**action, "description": "", "equivalent": ""}
    refuse(client, plan, tmp_path, "allowlist")
    assert client.calls == []  # guards run before any API call


@pytest.mark.parametrize("params", [["deployId"], "dep-abc", None])
def test_non_object_params_are_refused_with_guard_error(params):
    with pytest.raises(rr.GuardError):
        rr.validate_action({"kind": "rollback", "params": params})


@pytest.mark.parametrize("value", ["\u0663", "\u00b2", " 2", "2 "])
def test_non_ascii_or_padded_digits_are_refused(value):
    with pytest.raises(rr.GuardError):
        rr.validate_action({"kind": "set_env_var",
                            "params": {"key": "WEB_CONCURRENCY", "value": value}})


def drift_new_deploy(client):
    client.deploys.append(make_deploy("dep-surprise1", "live", created=-1, finished=-1))


def drift_auto_deploy(client):
    client.service["autoDeploy"] = "no"


def drift_concurrency(client):
    client.concurrency = "4"


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        (drift_new_deploy, "latestDeployId"),
        (drift_auto_deploy, "autoDeploy"),
        (drift_concurrency, "WEB_CONCURRENCY"),
    ],
)
def test_fingerprint_drift_is_refused(tmp_path, mutate, field):
    client = oom_client()
    plan = make_plan(client)
    mutate(client)
    refuse(client, plan, tmp_path, f"service changed since the plan was made.*{field}")


def test_deploy_in_progress_is_refused(tmp_path):
    building = make_deploy("dep-build1", "build_in_progress", created=-2)
    client = oom_client(deploys=[OLD, STALE_LIVE, building])
    plan = make_plan(client)  # fingerprint matches, so the in-progress guard is what fires
    refuse(client, plan, tmp_path, "dep-build1 is build_in_progress")


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def test_dry_run_sends_nothing(tmp_path):
    clock = FakeClock()
    client = oom_client(clock)
    code, lines = run_apply(client, make_plan(client), clock, tmp_path, dry_run=True)
    assert code == rr.EXIT_OK
    assert client.mutations == []
    assert not (tmp_path / "audit.jsonl").exists()
    assert any(line.startswith(f"[dry-run] PUT {ENV_PATH}") for line in lines)


def test_apply_oom_plan_happy_path(tmp_path):
    clock = FakeClock()
    client = oom_client(clock, deploy_response=202)
    code, lines = run_apply(client, make_plan(client), clock, tmp_path)

    assert code == rr.EXIT_OK, lines
    assert client.mutations == [
        ("PUT", ENV_PATH, {"value": "2"}),
        ("POST", f"/services/{SID}/deploys", {"clearCache": "do_not_clear"}),
    ]
    assert any("dep-auto1 is live" in line for line in lines)  # found via newest-deploy fallback
    records = audit_lines(tmp_path)
    assert [r.get("action") or r.get("verify") for r in records] == [
        "set_env_var", "trigger_deploy", "passed",
    ]
    assert all("value" not in r and "body" not in r for r in records)


def test_apply_bad_deploy_plan_happy_path(tmp_path):
    clock = FakeClock()
    client = bad_deploy_client(clock)
    code, lines = run_apply(client, make_plan(client), clock, tmp_path)

    assert code == rr.EXIT_OK, lines
    assert client.mutations == [
        ("PATCH", f"/services/{SID}", {"autoDeploy": "no"}),
        ("POST", f"/services/{SID}/rollback", {"deployId": "dep-old1"}),
    ]
    records = audit_lines(tmp_path)
    assert records[1]["deployId"] == "dep-rb1"
    assert records[-1]["verify"] == "passed"
    assert "dep-rb1" in records[-1]["detail"]


@pytest.mark.parametrize(
    ("error", "status", "error_text"),
    [
        (rr.RenderAPIError(400, "artifact unavailable"), 400, "artifact unavailable"),
        (urllib.error.URLError("connection reset"), None, "connection reset"),
    ],
    ids=["api-error", "network-error"],
)
def test_apply_stops_when_a_mutating_request_fails(tmp_path, error, status, error_text):
    clock = FakeClock()
    client = bad_deploy_client(clock)
    plan = make_plan(client)
    client.routes[("POST", f"/services/{SID}/rollback")] = error
    code, lines = run_apply(client, plan, clock, tmp_path)

    assert code == rr.EXIT_ERROR
    assert [m[:2] for m in client.mutations] == [
        ("PATCH", f"/services/{SID}"),
        ("POST", f"/services/{SID}/rollback"),
    ]
    assert client.calls[-1][:2] == ("POST", f"/services/{SID}/rollback")  # nothing after
    records = audit_lines(tmp_path)
    assert len(records) == 2
    assert records[-1]["action"] == "rollback"
    assert records[-1]["status"] == status
    assert error_text in records[-1]["error"]
    assert any("patch_auto_deploy" in line and "Completed" in line for line in lines)
    assert any("may or may not have reached Render" in line for line in lines) == (status is None)


def test_verify_fails_when_deploy_fails(tmp_path):
    clock = FakeClock()
    client = oom_client(clock, rollout=("queued", "update_failed"), deploy_response=201)
    code, lines = run_apply(client, make_plan(client), clock, tmp_path)
    assert code == rr.EXIT_VERIFY_FAILED
    assert len(client.mutations) == 2
    assert audit_lines(tmp_path)[-1]["verify"] == "failed"
    assert any("update_failed" in line for line in lines)


def test_verify_fails_on_new_oom_after_live(tmp_path):
    clock = FakeClock()
    # Rollout goes live at NOW+30s; the watch covers NOW+30s..NOW+5m30s.
    client = oom_client(clock, events=OOMS + [oom("evt-o3", 2)])
    code, lines = run_apply(client, make_plan(client), clock, tmp_path)
    assert code == rr.EXIT_VERIFY_FAILED, lines
    assert len(client.mutations) == 2
    assert "1 server_failed events" in audit_lines(tmp_path)[-1]["detail"]


def test_verify_times_out_when_deploy_never_goes_live(tmp_path):
    clock = FakeClock()
    client = oom_client(clock, rollout=("update_in_progress",))
    code, lines = run_apply(client, make_plan(client), clock, tmp_path)
    assert code == rr.EXIT_VERIFY_FAILED
    assert clock.now - NOW > rr.DEPLOY_TIMEOUT
    assert "not live after 20m" in audit_lines(tmp_path)[-1]["detail"]
    assert len(client.mutations) == 2


# ---------------------------------------------------------------------------
# Client and helpers
# ---------------------------------------------------------------------------


def test_paginate_follows_cursor(monkeypatch):
    monkeypatch.setattr(rr, "PAGE_SIZE", 2)
    pages = {
        None: [{"deploy": {"id": "a"}, "cursor": "c1"}, {"deploy": {"id": "b"}, "cursor": "c2"}],
        "c2": [{"deploy": {"id": "c"}, "cursor": "c3"}, {"deploy": {"id": "d"}, "cursor": "c4"}],
        "c4": [{"deploy": {"id": "e"}, "cursor": "c5"}],
    }
    client = FakeClient({("GET", "/x"): lambda q, b: (200, pages[q.get("cursor")])})
    items = rr.paginate(client, "/x", "deploy", {"foo": "bar"})
    assert [i["id"] for i in items] == ["a", "b", "c", "d", "e"]
    assert [q.get("cursor") for _, _, q, _ in client.calls] == [None, "c2", "c4"]
    assert all(q["limit"] == 2 and q["foo"] == "bar" for _, _, q, _ in client.calls)


@pytest.fixture
def local_api():
    state = {"flaky": 0, "auth": []}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body=None, headers=()):
            payload = b"" if body is None else json.dumps(body).encode()
            self.send_response(status)
            for key, value in headers:
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _route(self):
            state["auth"].append(self.headers.get("Authorization"))
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            if self.path.startswith("/v1/flaky"):
                state["flaky"] += 1
                if state["flaky"] == 1:
                    return self._send(429, {"message": "slow down"}, [("Retry-After", "0")])
                return self._send(200, {"ok": True})
            if self.path == "/v1/accepted":
                return self._send(202)
            return self._send(404, {"message": "not found"})

        do_GET = do_POST = _route

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1/", state
    finally:
        server.shutdown()
        server.server_close()


def test_render_client_against_local_server(local_api, monkeypatch):
    for var in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    base_url, state = local_api
    sleeps = []
    client = rr.RenderClient("test-key", base_url, sleep=sleeps.append)

    assert client.request("GET", "/flaky", query={"a": "1"}) == (200, {"ok": True})
    assert state["flaky"] == 2 and len(sleeps) == 1 and 0 <= sleeps[0] <= 1

    assert client.request("POST", "/accepted", body={"clearCache": "clear"}) == (202, None)

    with pytest.raises(rr.RenderAPIError) as excinfo:
        client.request("GET", "/missing")
    assert excinfo.value.status == 404
    assert excinfo.value.message == "not found"
    assert set(state["auth"]) == {"Bearer test-key"}


def test_parse_time_variants():
    assert rr.parse_time("2026-10-11T12:00:00Z") == NOW
    assert rr.parse_time("2026-10-11T12:00:00.123Z").microsecond == 123000
    parsed = rr.parse_time("2026-10-11T12:00:00.123456789Z")
    assert parsed.microsecond == 123456 and parsed.tzinfo is not None
    assert rr.parse_time("2026-10-11T12:00:00") == NOW  # naive is treated as UTC
    assert rr.parse_time("") is None


def test_parse_window():
    assert rr.parse_window("90m") == timedelta(minutes=90)
    assert rr.parse_window("2h") == timedelta(hours=2)
    assert rr.parse_window("1d") == timedelta(days=1)
    with pytest.raises(argparse.ArgumentTypeError):
        rr.parse_window("2x")


def test_main_without_api_key_is_an_error(monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    assert rr.main(["plan", "--service", "srv-x"]) == rr.EXIT_ERROR


def test_main_apply_refuses_expired_plan_before_any_network_call(monkeypatch, tmp_path):
    plan = make_plan(oom_client())
    plan["expiresAt"] = at(-1)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    def no_network(*args, **kwargs):
        raise AssertionError("network call before guards")

    monkeypatch.setenv("RENDER_API_KEY", "test-key")
    monkeypatch.setenv("RENDER_API_BASE", "http://127.0.0.1:9/v1")
    monkeypatch.setattr(rr.RenderClient, "request", no_network)
    code = rr.main([
        "apply", "--plan", str(plan_path), "--confirm", SID,
        "--audit-log", str(tmp_path / "audit.jsonl"),
    ])
    assert code == rr.EXIT_REFUSED
    assert not (tmp_path / "audit.jsonl").exists()
