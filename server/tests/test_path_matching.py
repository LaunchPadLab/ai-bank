"""Glob -> regex translation (recursive ** semantics) and rules_for_path."""

import pytest

from aibank_mcp.catalog import build_catalog
from aibank_mcp.search import compile_glob, glob_matches, normalize_path


@pytest.mark.parametrize(
    "glob,path,expected",
    [
        ("app/models/**/*.rb", "app/models/user.rb", True),
        ("app/models/**/*.rb", "app/models/concerns/auditable.rb", True),
        ("app/models/**/*.rb", "app/models.rb", False),  # needs the slash after models
        ("app/models/**/*.rb", "app/controllers/users_controller.rb", False),
        ("app/**/*.rb", "app/models/deep/nested/thing.rb", True),
        ("test/**/*.rb", "test/models/user_test.rb", True),
        ("test/**/*.rb", "app/models/user.rb", False),
        ("*.rb", "foo.rb", True),
        ("*.rb", "sub/foo.rb", False),  # single * does not cross a slash
    ],
)
def test_glob_matches(glob, path, expected):
    assert glob_matches(compile_glob(glob), path) is expected


def test_normalize_path():
    assert normalize_path("./app/models/x.rb") == "app/models/x.rb"
    assert normalize_path("/app/models/x.rb") == "app/models/x.rb"
    assert normalize_path("app\\models\\x.rb") == "app/models/x.rb"


def test_rules_for_path_matches_and_general(tmp_kb):
    cat = build_catalog(tmp_kb)

    res = cat.rules_for_path("app/widgets/button.rb")
    assert [m.name for m in res.matched] == ["widgets"]
    assert res.matched[0].matched_glob == "app/widgets/**/*.rb"
    assert "Widget Conventions" in res.matched[0].body
    assert [g.name for g in res.general] == ["general-rule"]

    # Non-matching path -> only general rules.
    miss = cat.rules_for_path("README.md")
    assert miss.matched == []
    assert [g.name for g in miss.general] == ["general-rule"]

    # General rules can be excluded.
    no_general = cat.rules_for_path("app/widgets/button.rb", include_general=False)
    assert no_general.general == []


def test_rules_for_path_real_corpus(real_catalog):
    res = real_catalog.rules_for_path("app/models/order.rb")
    matched = {m.name for m in res.matched}
    assert "models" in matched
    assert res.general  # principles/cli/git-conventions always apply
    assert "Model Conventions" in next(m.body for m in res.matched if m.name == "models")
