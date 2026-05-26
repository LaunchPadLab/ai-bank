"""Lock the exact frontmatter shapes the ai-bank corpus uses."""

from aibank_mcp.frontmatter import parse_frontmatter, strip_frontmatter


def test_scalar_and_no_frontmatter():
    meta, body = parse_frontmatter("---\nname: foo\ndescription: bar baz\n---\n\n# Title\n")
    assert meta == {"name": "foo", "description": "bar baz"}
    assert body.strip() == "# Title"

    meta2, body2 = parse_frontmatter("# Just a doc\n")
    assert meta2 == {}
    assert body2 == "# Just a doc\n"


def test_folded_block_scalar_is_flattened():
    text = "---\ndescription: >-\n  line one\n  line two\n---\nbody\n"
    meta, _ = parse_frontmatter(text)
    assert meta["description"] == "line one line two"


def test_inline_and_block_lists():
    inline, _ = parse_frontmatter("---\nskills: [a, b, c]\n---\n")
    assert inline["skills"] == ["a", "b", "c"]

    block, _ = parse_frontmatter('---\npaths:\n  - "app/models/**/*.rb"\n  - "test/**/*.rb"\n---\n')
    assert block["paths"] == ["app/models/**/*.rb", "test/**/*.rb"]


def test_booleans_and_comma_scalar():
    meta, _ = parse_frontmatter(
        "---\nuser-invocable: true\ndisable-model-invocation: false\n"
        "allowed-tools: Read, Write, Edit\n---\n"
    )
    assert meta["user-invocable"] is True
    assert meta["disable-model-invocation"] is False
    # allowed-tools stays a comma string at the parser level; the loader splits it.
    assert meta["allowed-tools"] == "Read, Write, Edit"


def test_strip_frontmatter():
    assert strip_frontmatter("---\nname: x\n---\nhello\n") == "hello\n"
    assert strip_frontmatter("no frontmatter\n") == "no frontmatter\n"
