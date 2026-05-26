"""Lightweight, deterministic search + path-glob matching.

Keyword scoring (no embeddings) is the right tool for ~100 short docs whose descriptions
are hand-written "Use when ..." trigger phrases — it is fast, deterministic, and testable.
The glob matcher gives recursive ``**`` semantics that ``fnmatch`` cannot, with zero deps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Words that appear in almost every "Use when ..." description and add only noise.
_STOPWORDS = frozenset(
    {
        "use", "when", "the", "a", "an", "for", "or", "and", "with", "to", "of", "in",
        "on", "by", "mentions", "proactively", "this", "that", "your", "you", "it",
    }
)

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)

# Field weights — description carries the curated trigger vocabulary, so it ranks high.
_W_NAME = 5.0
_W_DESCRIPTION = 3.0
_W_HEADING = 1.0
_BONUS_EXACT_NAME = 10.0
_BONUS_PHRASE = 4.0
_BONUS_COVERAGE = 2.0


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics (so hyphens break words), drop stopwords."""
    if not text:
        return []
    return [tok for tok in _TOKEN_SPLIT_RE.split(text.lower()) if tok and tok not in _STOPWORDS]


def _heading_text(body: str) -> str:
    return " ".join(_HEADING_RE.findall(body or ""))


@dataclass
class SearchDoc:
    kind: str  # "skill" | "agent" | "rule"
    name: str
    description: str
    name_tokens: frozenset[str]
    desc_tokens: frozenset[str]
    heading_tokens: frozenset[str]

    @classmethod
    def build(cls, kind: str, name: str, description: str, body: str) -> SearchDoc:
        return cls(
            kind=kind,
            name=name,
            description=description,
            name_tokens=frozenset(tokenize(name)),
            desc_tokens=frozenset(tokenize(description)),
            heading_tokens=frozenset(tokenize(_heading_text(body))),
        )


def score_doc(query: str, query_terms: list[str], doc: SearchDoc) -> tuple[float, list[str]]:
    """Return ``(score, matched_terms)`` for a single doc against a query."""
    score = 0.0
    matched: set[str] = set()
    for term in query_terms:
        if term in doc.name_tokens:
            score += _W_NAME
            matched.add(term)
        if term in doc.desc_tokens:
            score += _W_DESCRIPTION
            matched.add(term)
        if term in doc.heading_tokens:
            score += _W_HEADING
            matched.add(term)

    q_norm = query.strip().lower()
    if q_norm and q_norm == doc.name.lower():
        score += _BONUS_EXACT_NAME
    if q_norm and q_norm in doc.description.lower():
        score += _BONUS_PHRASE
    if query_terms:
        score += (len(matched) / len(query_terms)) * _BONUS_COVERAGE

    return score, sorted(matched)


@dataclass
class ScoredDoc:
    doc: SearchDoc
    score: float
    matched_terms: list[str] = field(default_factory=list)


def search(docs: list[SearchDoc], query: str, kind: str = "all", limit: int = 15) -> list[ScoredDoc]:
    """Rank ``docs`` against ``query``. ``kind`` filters by doc kind ('all' keeps everything)."""
    query_terms = tokenize(query)
    if not query_terms:
        return []

    results: list[ScoredDoc] = []
    for doc in docs:
        if kind != "all" and doc.kind != kind:
            continue
        score, matched = score_doc(query, query_terms, doc)
        if score > 0:
            results.append(ScoredDoc(doc=doc, score=score, matched_terms=matched))

    # Highest score first; stable tie-break by (kind, name) for determinism.
    results.sort(key=lambda r: (-r.score, r.doc.kind, r.doc.name))
    return results[: max(0, limit)]


# --------------------------------------------------------------------------- #
# Path-glob matching (git-style ``**`` semantics, zero dependencies)
# --------------------------------------------------------------------------- #


def _translate_glob(glob: str) -> str:
    """Translate a git-style path glob to an anchored regex string.

    ``**/`` -> ``(?:.*/)?`` (zero or more dirs), ``**`` -> ``.*``, ``*`` -> ``[^/]*``,
    ``?`` -> ``[^/]``; every other character is matched literally.
    """
    out = ["^"]
    i, n = 0, len(glob)
    while i < n:
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    out.append("$")
    return "".join(out)


def compile_glob(glob: str) -> re.Pattern[str]:
    return re.compile(_translate_glob(glob))


def normalize_path(path: str) -> str:
    """Normalize a caller-supplied path: forward slashes, no leading ``./`` or ``/``."""
    p = path.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def glob_matches(compiled: re.Pattern[str], path: str) -> bool:
    return compiled.match(normalize_path(path)) is not None
