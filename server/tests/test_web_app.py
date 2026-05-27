"""HTTP surface: health, catalog endpoints, the in-app asset viewer, and static assets."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aibank_web.app import STATIC_DIR, build_app
from aibank_web.config import ChatSettings


@pytest.fixture(scope="module")
def client():
    app = build_app(ChatSettings.from_env())
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_catalog_overview(client):
    data = client.get("/api/catalog/overview").json()
    assert data["skills"] > 0 and data["agents"] > 0 and data["rules"] > 0


def test_catalog_names(client):
    data = client.get("/api/catalog/names").json()
    assert data["skills"] and data["agents"] and data["rules"]


def test_asset_skill_detail(client):
    names = client.get("/api/catalog/names").json()
    name = names["skills"][0]
    data = client.get(f"/api/asset/skill/{name}").json()
    assert data["kind"] == "skill"
    assert data["name"] == name
    assert data["body"]


def test_asset_agent_and_rule(client):
    names = client.get("/api/catalog/names").json()
    agent = client.get(f"/api/asset/agent/{names['agents'][0]}").json()
    assert agent["kind"] == "agent" and agent["body"]
    rule = client.get(f"/api/asset/rule/{names['rules'][0]}").json()
    assert rule["kind"] == "rule" and rule["body"]


def test_asset_unknown_is_404(client):
    assert client.get("/api/asset/skill/not-a-real-skill-xyz").status_code == 404
    assert client.get("/api/asset/widget/foo").status_code == 404


def test_index_and_asset_pages_served(client):
    home = client.get("/")
    assert home.status_code == 200 and "ai-bank" in home.text
    # The asset page is a static shell; the client fills it in from the JSON API.
    assert client.get("/a/skill/anything").status_code == 200


def test_vendored_js_present_and_nonempty():
    for name in ("marked.min.js", "dompurify.min.js"):
        path = STATIC_DIR / "js" / "vendor" / name
        assert path.is_file() and path.stat().st_size > 1000
