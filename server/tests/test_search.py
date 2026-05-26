"""Keyword ranking behavior."""

from aibank_mcp.search import tokenize


def test_tokenize_drops_stopwords_and_splits_hyphens():
    assert tokenize("Use when setting up password-reset") == ["setting", "up", "password", "reset"]
    assert tokenize("") == []


def test_empty_query_returns_nothing(real_catalog):
    assert real_catalog.search("") == []
    assert real_catalog.search("   ") == []


def test_exact_name_ranks_first(real_catalog):
    hits = real_catalog.search("policy-patterns", limit=5)
    assert hits and hits[0].name == "policy-patterns"


def test_trigger_phrase_search(real_catalog):
    names = [h.name for h in real_catalog.search("password reset", limit=8)]
    assert "authentication-flow" in names


def test_kind_filter(real_catalog):
    hits = real_catalog.search("deploy", kind="skill", limit=10)
    assert hits
    assert all(h.kind == "skill" for h in hits)
    assert hits[0].name == "render-deploy"  # proves codex merge participates in search


def test_results_sorted_by_score_desc(real_catalog):
    scores = [h.score for h in real_catalog.search("rails controller", limit=10)]
    assert scores == sorted(scores, reverse=True)
