"""Data model for the ai-bank catalog.

Two kinds of dataclass live here, all dependency-free (no FastMCP import):

* **Internal records** (``Skill``/``Agent``/``Rule``/``ReferenceFile``) hold the parsed
  asset plus its body and filesystem location. They are frozen so the catalog is an
  immutable snapshot after build (safe for concurrent HTTP requests).
* **Wire shapes** (``*Summary``/``*Detail``/``SearchHit``/...) are what the MCP tools
  return. FastMCP turns these into structured output. They deliberately omit absolute
  filesystem paths so nothing leaks to clients.
"""

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# Internal records (hold bodies + absolute paths; never returned directly)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ReferenceFile:
    """A supporting doc inside a skill's ``reference/`` or ``references/`` dir."""

    filename: str  # e.g. "sessions.md"
    rel_path: str  # e.g. "reference/sessions.md" (preserves which spelling won)
    abs_path: str  # absolute path, for lazy body reads (internal only)


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    description: str
    source: str  # "claude" | "codex"
    allowed_tools: tuple[str, ...]
    user_invocable: bool | None  # tri-state: None when key absent
    disable_model_invocation: bool | None
    argument_hint: str | None
    context: str | None  # e.g. "fork"
    agent: str | None  # e.g. "Explore"
    reference_dir: str | None  # "reference" | "references" | None
    references: tuple[ReferenceFile, ...]
    dir_path: str
    body: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class Agent:
    name: str
    description: str
    model: str | None
    skills: tuple[str, ...]  # cross-links to Skill.name (may include unknowns)
    permission_mode: str | None
    disallowed_tools: tuple[str, ...]
    max_turns: int | None
    memory: str | None
    background: bool | None
    isolation: str | None
    file_path: str
    body: str = field(repr=False)  # the system prompt


@dataclass(frozen=True, slots=True)
class Rule:
    name: str  # filename stem, e.g. "models"
    paths: tuple[str, ...]  # glob list; empty => general/always-applicable
    is_general: bool
    description: str | None
    file_path: str
    body: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class LoadWarning:
    path: str
    reason: str


# --------------------------------------------------------------------------- #
# Wire shapes (returned by MCP tools -> structured output)
# --------------------------------------------------------------------------- #


@dataclass
class ReferenceInfo:
    filename: str
    rel_path: str


@dataclass
class SkillRef:
    """A lightweight reference to a skill (used for agent cross-links)."""

    name: str
    description: str


@dataclass
class SkillSummary:
    name: str
    description: str
    source: str
    user_invocable: bool | None
    disable_model_invocation: bool | None
    argument_hint: str | None
    has_references: bool
    reference_filenames: list[str]


@dataclass
class SkillDetail:
    name: str
    description: str
    source: str
    allowed_tools: list[str]
    user_invocable: bool | None
    disable_model_invocation: bool | None
    argument_hint: str | None
    context: str | None
    agent: str | None
    references: list[ReferenceInfo]
    used_by_agents: list[str]
    body: str


@dataclass
class AgentSummary:
    name: str
    description: str
    model: str | None
    skills: list[str]


@dataclass
class AgentDetail:
    name: str
    description: str
    model: str | None
    skills_resolved: list[SkillRef]
    skills_unresolved: list[str]
    body: str


@dataclass
class RuleSummary:
    name: str
    paths: list[str]
    is_general: bool
    description: str | None


@dataclass
class RuleDetail:
    name: str
    paths: list[str]
    is_general: bool
    description: str | None
    body: str


@dataclass
class SearchHit:
    kind: str  # "skill" | "agent" | "rule"
    name: str
    description: str
    score: float
    matched_terms: list[str]


@dataclass
class MatchedRule:
    name: str
    paths: list[str]
    matched_glob: str
    body: str


@dataclass
class GeneralRule:
    name: str
    body: str


@dataclass
class RulesForPathResult:
    path: str
    matched: list[MatchedRule]
    general: list[GeneralRule]


@dataclass
class CatalogOverview:
    skills: int
    agents: int
    rules: int
    general_rules: int
    render_skills_included: bool
    load_warnings: list[LoadWarning]
