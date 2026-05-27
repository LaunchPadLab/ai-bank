"""System prompt construction for the grounded ai-bank assistant.

The prompt is built once at startup into two text blocks:

* **Instructions** -- frozen guidance on grounding, citations, the discovery workflow, and
  output style. Byte-stable across the process lifetime.
* **Catalog index** -- counts plus every skill/agent/rule name + one-line description, rendered
  deterministically from the (already name-sorted) catalog. This closed-vocabulary index is the
  main grounding lever: the model learns exactly what exists and which names to pass to the
  tools, and can answer "is there a skill for X?" without a list_catalog round-trip.

A single ``cache_control`` breakpoint sits on the last (index) block. Because the API renders
``tools`` -> ``system`` -> ``messages``, that one breakpoint caches the tool schemas AND the
whole system prompt together. Nothing here may vary per request (no timestamps, ids, or user
data) or the cache silently misses.
"""

from __future__ import annotations

from aibank_mcp.catalog import Catalog

_INSTRUCTIONS = """\
You are the ai-bank assistant. ai-bank is a read-only catalog of reusable AI-tooling assets for \
Rails/Hotwire development:
- Skills: instructional SKILL.md packages (with optional reference docs).
- Agents: specialist system prompts that define an expert persona.
- Rules: path-scoped coding conventions that apply when editing matching files.

Your job is to answer questions about this catalog and the best practices it encodes.

Grounding
- Answer ONLY from the ai-bank catalog, retrieved with your tools. Do not answer from prior \
knowledge of Rails, Hotwire, or what these assets might contain.
- Before stating any specific fact about a skill, agent, or rule (its guidance, steps, options, \
or reference contents), you must have retrieved it this conversation with get_skill, get_agent, \
get_rule, or get_skill_reference. The catalog index below lists what EXISTS, but not the bodies \
-- never quote or paraphrase a body you have not fetched.
- If the catalog does not cover the topic, say so plainly: state that ai-bank has no skill, \
agent, or rule for it, and (if search surfaced near-misses) point to the closest available \
assets. Never invent an asset name, reference filename, or body.

Workflow
- Use search to discover relevant assets, then fetch full content with get_skill / get_agent / \
get_rule. get_skill returns a skill's reference filenames; fetch a specific one with \
get_skill_reference. For questions about which conventions apply to a file, call \
get_rules_for_path with the repo-relative path. Use list_catalog to browse a type when search \
is too narrow. Call search whenever the answer depends on catalog contents you have not already \
retrieved in this conversation.

Citations
- Cite every asset you draw on, inline, using these exact tokens so the interface can link them:
  - a skill: [skill:<name>]  e.g. [skill:caching-strategies]
  - an agent: [agent:<name>]  e.g. [agent:rails-architecture]
  - a rule:  [rule:<name>]   e.g. [rule:models]
  - a skill reference doc: [skill:<name>#<filename>]  e.g. [skill:testing-patterns#fixtures.md]
- Use the exact asset name from the tool results. Place a citation right where you use the fact.

Style
- Be concise and direct. Lead with the answer, then the supporting detail. Prefer short \
paragraphs and tight lists. Don't pad with restatements of the question.
- Use Markdown. Keep code snippets minimal and only when they come from a retrieved asset.\
"""


def _render_index(catalog: Catalog) -> str:
    overview = catalog.overview()
    lines: list[str] = [
        "# ai-bank catalog index",
        "",
        (
            f"The catalog currently contains {overview.skills} skills, {overview.agents} agents, "
            f"and {overview.rules} rules. The names and descriptions below are the complete, "
            f"authoritative vocabulary -- if something is not listed here, it does not exist in "
            f"ai-bank. Bodies are NOT included; fetch them with the tools before quoting."
        ),
        "",
        f"## Skills ({overview.skills})",
    ]
    for s in catalog.list_skill_summaries("all"):
        lines.append(f"- {s.name}: {s.description}")

    lines += ["", f"## Agents ({overview.agents})"]
    for a in catalog.list_agent_summaries():
        lines.append(f"- {a.name}: {a.description}")

    lines += ["", f"## Rules ({overview.rules})"]
    for r in catalog.list_rule_summaries(include_general=True):
        if r.description:
            desc = r.description
        elif r.is_general:
            desc = "general (always applies)"
        elif r.paths:
            desc = "applies to: " + ", ".join(r.paths)
        else:
            desc = "—"
        lines.append(f"- {r.name}: {desc}")

    return "\n".join(lines)


def build_system_prompt(catalog: Catalog) -> list[dict]:
    """Return the system prompt as cacheable text blocks (instructions, then catalog index).

    The last block carries the ephemeral cache breakpoint, caching tools + system together.
    """
    return [
        {"type": "text", "text": _INSTRUCTIONS},
        {
            "type": "text",
            "text": _render_index(catalog),
            "cache_control": {"type": "ephemeral"},
        },
    ]
