"""YAML-frontmatter parser for ai-bank markdown assets.

VENDORED from ``codex/scripts/codex_transpose.py`` (``parse_frontmatter`` /
``read_markdown_with_frontmatter`` / ``FRONTMATTER_RE`` / ``strip_frontmatter``).
Kept dependency-free on purpose so the server installs cleanly via ``uvx``/``pipx``.

Keep behavior in sync with the codex script; the exact corpus shapes this must handle
(scalars, block scalars ``>``/``|``, inline ``[..]`` lists, YAML block lists, booleans)
are locked by ``tests/test_frontmatter.py``.
"""

import re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n?---\n?", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split leading ``---`` frontmatter from a markdown document.

    Returns ``(metadata, body)``. When there is no frontmatter, returns ``({}, text)``.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    metadata: dict = {}
    lines = match.group(1).splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith(" ") or ":" not in line:
            index += 1
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Block scalar (``>``/``|`` and their ``-`` chomping variants): join folded lines.
        if value in {">", ">-", "|", "|-"}:
            index += 1
            block = []
            while index < len(lines) and (lines[index].startswith(" ") or not lines[index].strip()):
                block.append(lines[index].strip())
                index += 1
            metadata[key] = " ".join(part for part in block if part)
            continue

        # Empty value followed by an indented ``- `` block list.
        if not value:
            index += 1
            values = []
            while index < len(lines) and lines[index].startswith(" "):
                item = lines[index].strip()
                if item.startswith("- "):
                    values.append(item[2:].strip().strip("'\""))
                index += 1
            metadata[key] = values
            continue

        # Inline list ``[a, b]``.
        if value.startswith("[") and value.endswith("]"):
            metadata[key] = [
                item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()
            ]
        elif value.lower() == "true":
            metadata[key] = True
        elif value.lower() == "false":
            metadata[key] = False
        else:
            metadata[key] = value.strip("'\"")
        index += 1

    return metadata, text[match.end() :]


def read_markdown_with_frontmatter(path) -> tuple[dict, str]:
    """Read a markdown file and return ``(metadata, body)``."""
    return parse_frontmatter(Path(path).read_text(encoding="utf-8"))


def strip_frontmatter(text: str) -> str:
    """Return ``text`` with a single leading frontmatter block removed."""
    return FRONTMATTER_RE.sub("", text, count=1)
