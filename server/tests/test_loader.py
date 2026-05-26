"""Loader behavior on a synthetic tree, plus a smoke pass over the real claude/ corpus."""

from aibank_mcp.config import AGENTS_SUBDIR, CLAUDE_DIR, RULES_SUBDIR, SKILLS_SUBDIR
from aibank_mcp.loader import load_agents, load_rules, load_skills


def test_load_skills_detects_both_reference_spellings_and_warns(tmp_kb):
    skills, warnings = load_skills(tmp_kb / CLAUDE_DIR / SKILLS_SUBDIR)
    by_name = {s.name: s for s in skills}

    assert set(by_name) == {"good-skill", "plural-skill"}  # broken-skill skipped

    assert by_name["good-skill"].reference_dir == "reference"
    assert [r.rel_path for r in by_name["good-skill"].references] == ["reference/details.md"]
    assert list(by_name["good-skill"].allowed_tools) == ["Read", "Write", "Edit"]

    assert by_name["plural-skill"].reference_dir == "references"
    assert by_name["plural-skill"].user_invocable is True
    # tri-state: absent key stays None, not False
    assert by_name["good-skill"].user_invocable is None

    assert any("broken-skill" in w.path and "SKILL.md" in w.reason for w in warnings)


def test_load_agents_skips_readme_and_parses_skills(tmp_kb):
    agents, _ = load_agents(tmp_kb / CLAUDE_DIR / AGENTS_SUBDIR)
    assert [a.name for a in agents] == ["test-agent"]  # README.md skipped
    assert list(agents[0].skills) == ["good-skill", "ghost-skill"]
    assert agents[0].model == "inherit"


def test_load_rules_paths_and_general(tmp_kb):
    rules, _ = load_rules(tmp_kb / CLAUDE_DIR / RULES_SUBDIR)
    by_name = {r.name: r for r in rules}
    assert set(by_name) == {"widgets", "general-rule"}  # README.md skipped

    assert list(by_name["widgets"].paths) == ["app/widgets/**/*.rb"]
    assert by_name["widgets"].is_general is False
    assert by_name["general-rule"].paths == ()
    assert by_name["general-rule"].is_general is True


def test_missing_directory_returns_empty(tmp_path):
    skills, warnings = load_skills(tmp_path / "does-not-exist")
    assert skills == [] and warnings == []


def test_real_corpus_loads_cleanly(repo_root):
    claude = repo_root / CLAUDE_DIR
    skills, sw = load_skills(claude / SKILLS_SUBDIR)
    agents, aw = load_agents(claude / AGENTS_SUBDIR)
    rules, rw = load_rules(claude / RULES_SUBDIR)

    assert len(skills) >= 40
    assert len(agents) >= 40
    assert len(rules) >= 15
    # Every asset has a non-empty name; the real tree should parse without warnings.
    assert all(s.name for s in skills)
    assert sw == [] and aw == [] and rw == []

    models_rule = next(r for r in rules if r.name == "models")
    assert "app/models/**/*.rb" in models_rule.paths
