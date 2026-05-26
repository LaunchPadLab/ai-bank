"""End-to-end MCP tests via the in-memory fastmcp Client (real registration, no sockets)."""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from aibank_mcp.server import build_server

EXPECTED_TOOLS = {
    "search",
    "catalog_overview",
    "list_skills",
    "get_skill",
    "list_skill_references",
    "get_skill_reference",
    "list_agents",
    "get_agent",
    "list_rules",
    "get_rule",
    "get_rules_for_path",
}


@pytest.fixture
def server(tmp_kb):
    return build_server(tmp_kb)


async def test_all_tools_registered_and_readonly(server):
    async with Client(server) as c:
        tools = await c.list_tools()
    assert {t.name for t in tools} == EXPECTED_TOOLS
    assert all(t.annotations and t.annotations.readOnlyHint for t in tools)


async def test_search_then_get_skill(server):
    async with Client(server) as c:
        hits = (await c.call_tool("search", {"query": "good", "kind": "skill"})).data
        assert any(h.name == "good-skill" for h in hits)

        detail = (await c.call_tool("get_skill", {"name": "good-skill"})).data
        assert detail.used_by_agents == ["test-agent"]
        assert "Good Skill" in detail.body
        assert detail.allowed_tools == ["Read", "Write", "Edit"]


async def test_get_rules_for_path(server):
    async with Client(server) as c:
        res = (await c.call_tool("get_rules_for_path", {"path": "app/widgets/button.rb"})).data
    assert [m.name for m in res.matched] == ["widgets"]
    assert res.matched[0].matched_glob == "app/widgets/**/*.rb"
    assert [g.name for g in res.general] == ["general-rule"]


async def test_skill_reference_and_error_paths(server):
    async with Client(server) as c:
        body = (
            await c.call_tool("get_skill_reference", {"name": "good-skill", "filename": "details"})
        ).data
        assert "More detail" in body

        with pytest.raises(ToolError, match="Unknown skill"):
            await c.call_tool("get_skill", {"name": "ghost"})
        with pytest.raises(ToolError, match="no reference"):
            await c.call_tool("get_skill_reference", {"name": "good-skill", "filename": "nope"})


async def test_agent_cross_links(server):
    async with Client(server) as c:
        detail = (await c.call_tool("get_agent", {"name": "test-agent"})).data
    assert [s.name for s in detail.skills_resolved] == ["good-skill"]
    assert detail.skills_unresolved == ["ghost-skill"]


async def test_resources_and_templates(server):
    async with Client(server) as c:
        resources = {str(r.uri) for r in await c.list_resources()}
        templates = {t.uriTemplate for t in await c.list_resource_templates()}
        assert {"aibank://skills", "aibank://agents", "aibank://rules"} <= resources
        assert "aibank://skill/{name}" in templates
        assert "aibank://skill/{name}/reference/{filename*}" in templates

        skill_body = (await c.read_resource("aibank://skill/good-skill"))[0].text
        assert "Good Skill" in skill_body
        ref_body = (await c.read_resource("aibank://skill/good-skill/reference/details.md"))[0].text
        assert "More detail" in ref_body


async def test_prompt_renders_with_arguments(server):
    async with Client(server) as c:
        prompts = {p.name for p in await c.list_prompts()}
        assert prompts == {"echo-cmd"}
        result = await c.get_prompt("echo-cmd", {"arguments": "hello world"})
    assert "Echo: hello world" in result.messages[0].content.text


async def test_real_tree_server_smoke(repo_root):
    """The real catalog wires up end-to-end and the flagship tool works."""
    async with Client(build_server(repo_root)) as c:
        ov = (await c.call_tool("catalog_overview", {})).data
        assert ov.skills > 40 and ov.agents > 40
        res = (await c.call_tool("get_rules_for_path", {"path": "app/models/order.rb"})).data
        assert "models" in {m.name for m in res.matched}
        assert len({p.name for p in await c.list_prompts()}) == 6
