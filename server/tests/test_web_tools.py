"""Tool dispatch over the catalog: schemas, not-found wording, and citation sources."""

from __future__ import annotations

from aibank_mcp.catalog import build_catalog
from aibank_mcp.config import resolve_repo_root

from aibank_web.tools import ANTHROPIC_TOOLS, execute_tool, tool_label


def _catalog():
    return build_catalog(resolve_repo_root())


def test_tool_schemas_are_static_and_well_formed():
    names = [t["name"] for t in ANTHROPIC_TOOLS]
    assert names == [
        "search",
        "get_skill",
        "get_skill_reference",
        "get_agent",
        "get_rule",
        "get_rules_for_path",
        "list_catalog",
    ]
    for tool in ANTHROPIC_TOOLS:
        assert tool["description"]
        assert tool["input_schema"]["type"] == "object"
        assert isinstance(tool["input_schema"]["properties"], dict)


def test_search_returns_results_without_sources():
    out = execute_tool(_catalog(), "search", {"query": "testing"})
    assert not out.is_error
    assert out.sources == ()
    assert out.content.startswith("[")  # JSON array of hits


def test_get_skill_unknown_uses_helpful_message():
    out = execute_tool(_catalog(), "get_skill", {"name": "definitely-not-a-real-skill"})
    assert out.is_error
    assert "Unknown skill" in out.content
    assert "search" in out.content


def test_get_skill_known_records_source():
    catalog = _catalog()
    name = catalog.skill_names()[0]
    out = execute_tool(catalog, "get_skill", {"name": name})
    assert not out.is_error
    assert out.sources and out.sources[0].kind == "skill"
    assert out.sources[0].name == name


def test_get_rules_for_path_records_rule_sources():
    out = execute_tool(_catalog(), "get_rules_for_path", {"path": "app/models/user.rb"})
    assert not out.is_error
    assert all(s.kind == "rule" for s in out.sources)


def test_unknown_tool_is_an_error():
    out = execute_tool(_catalog(), "frobnicate", {})
    assert out.is_error
    assert "Unknown tool" in out.content


def test_list_catalog_bad_kind():
    out = execute_tool(_catalog(), "list_catalog", {"kind": "widgets"})
    assert out.is_error


def test_tool_label_is_human_readable():
    assert "Searching" in tool_label("search", {"query": "caching"})
    assert "rails" in tool_label("get_agent", {"name": "rails"})
