"""Catalog indexing, cross-links, render merge, name normalization, and lazy reference reads."""

import pytest

from aibank_mcp.catalog import build_catalog


@pytest.fixture
def catalog(tmp_kb):
    return build_catalog(tmp_kb)


def test_render_skill_merged_by_allowlist_only(catalog):
    names = {s.name: s.source for s in catalog.skills}
    assert names.get("render-deploy") == "codex"  # on the allowlist -> merged
    assert "codex-extra" not in names  # not on the allowlist -> ignored
    assert names.get("good-skill") == "claude"
    assert catalog.render_skills_included is True


def test_source_filter(catalog):
    claude_only = catalog.list_skill_summaries("claude")
    assert all(s.source == "claude" for s in claude_only)
    assert "render-deploy" not in {s.name for s in claude_only}
    assert "render-deploy" in {s.name for s in catalog.list_skill_summaries("codex")}


def test_skill_detail_and_agent_cross_links(catalog):
    good = catalog.skill_detail("good-skill")
    assert good.used_by_agents == ["test-agent"]
    assert [r.rel_path for r in good.references] == ["reference/details.md"]

    agent = catalog.agent_detail("test-agent")
    assert [s.name for s in agent.skills_resolved] == ["good-skill"]
    assert agent.skills_unresolved == ["ghost-skill"]


def test_name_normalization(catalog):
    assert catalog.skill_detail("Good-Skill.md").name == "good-skill"
    assert catalog.skill_detail("/good-skill").name == "good-skill"
    assert catalog.skill_detail("nope") is None


def test_read_skill_reference_accepts_stem_or_filename(catalog):
    assert "More detail" in catalog.read_skill_reference("good-skill", "details")
    assert "More detail" in catalog.read_skill_reference("good-skill", "details.md")
    assert catalog.read_skill_reference("good-skill", "missing") is None
    assert catalog.read_skill_reference("nope", "details") is None


def test_reference_read_is_cached(catalog):
    catalog.read_skill_reference("good-skill", "details")
    assert any(p.endswith("details.md") for p in catalog._ref_cache)


def test_overview(catalog):
    ov = catalog.overview()
    assert ov.skills == 3  # good, plural, render-deploy
    assert ov.agents == 1
    assert ov.rules == 2
    assert ov.general_rules == 1
    assert any("broken-skill" in w.path for w in ov.load_warnings)


def test_real_catalog_counts(real_catalog):
    ov = real_catalog.overview()
    assert ov.skills > 40 and ov.agents > 40 and ov.rules >= 15
    assert ov.render_skills_included is True
    assert ov.load_warnings == []
