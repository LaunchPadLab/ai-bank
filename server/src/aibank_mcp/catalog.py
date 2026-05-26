"""In-memory catalog: load once, index, and serve wire shapes to the MCP layer.

The catalog is built at startup and treated as an immutable snapshot (records are frozen
dataclasses). The only mutable state is a small cache of lazily-read reference-file bodies,
whose worst-case race is a redundant, idempotent file read — safe without locks.
"""

from __future__ import annotations

from pathlib import Path

from . import search as _search
from .config import (
    AGENTS_SUBDIR,
    CLAUDE_DIR,
    CODEX_DIR,
    RULES_SUBDIR,
    SKILLS_SUBDIR,
    within_root,
)
from .loader import RENDER_ONLY_SKILL_NAMES, load_agents, load_rules, load_skills
from .models import (
    Agent,
    AgentDetail,
    AgentSummary,
    CatalogOverview,
    GeneralRule,
    LoadWarning,
    MatchedRule,
    ReferenceInfo,
    Rule,
    RuleDetail,
    RuleSummary,
    RulesForPathResult,
    SearchHit,
    Skill,
    SkillDetail,
    SkillRef,
    SkillSummary,
)


def _norm(name: str) -> str:
    """Normalize a name/slug arg: lowercase, drop a stray '.md' suffix or leading slash."""
    return name.strip().lower().lstrip("/").removesuffix(".md")


def build_catalog(repo_root: Path, *, include_render_skills: bool = True) -> "Catalog":
    """Load skills/agents/rules from ``repo_root`` into a :class:`Catalog`."""
    claude = repo_root / CLAUDE_DIR
    skills, warnings = load_skills(claude / SKILLS_SUBDIR, source="claude")

    if include_render_skills:
        codex_skills, codex_warnings = load_skills(repo_root / CODEX_DIR / SKILLS_SUBDIR, "codex")
        known = {_norm(s.name) for s in skills}
        for skill in codex_skills:
            if skill.name in RENDER_ONLY_SKILL_NAMES and _norm(skill.name) not in known:
                skills.append(skill)
        # Only surface codex parse problems for the render skills we actually merged.
        warnings.extend(w for w in codex_warnings if any(n in w.path for n in RENDER_ONLY_SKILL_NAMES))

    agents, agent_warnings = load_agents(claude / AGENTS_SUBDIR)
    rules, rule_warnings = load_rules(claude / RULES_SUBDIR)
    warnings.extend(agent_warnings)
    warnings.extend(rule_warnings)

    return Catalog(repo_root, skills, agents, rules, warnings)


class Catalog:
    def __init__(
        self,
        repo_root: Path,
        skills: list[Skill],
        agents: list[Agent],
        rules: list[Rule],
        load_warnings: list[LoadWarning],
    ) -> None:
        self.repo_root = repo_root
        self.skills = tuple(sorted(skills, key=lambda s: s.name.lower()))
        self.agents = tuple(sorted(agents, key=lambda a: a.name.lower()))
        self.rules = tuple(sorted(rules, key=lambda r: r.name.lower()))
        self.load_warnings = tuple(load_warnings)
        self.render_skills_included = any(s.source == "codex" for s in self.skills)

        self._skill_by_name = {_norm(s.name): s for s in self.skills}
        self._agent_by_name = {_norm(a.name): a for a in self.agents}
        self._rule_by_name = {_norm(r.name): r for r in self.rules}

        self._general_rules = tuple(r for r in self.rules if r.is_general)
        self._path_rules = tuple(r for r in self.rules if not r.is_general)

        # Precompile each path rule's globs once: name -> [(glob, compiled_regex)].
        self._rule_globs = {
            r.name: [(g, _search.compile_glob(g)) for g in r.paths] for r in self._path_rules
        }

        # Reverse cross-link index: skill name -> [agent names that list it].
        self._agents_for_skill: dict[str, list[str]] = {}
        for agent in self.agents:
            for skill_name in agent.skills:
                self._agents_for_skill.setdefault(_norm(skill_name), []).append(agent.name)
        for names in self._agents_for_skill.values():
            names.sort(key=str.lower)

        self._search_docs = [
            _search.SearchDoc.build("skill", s.name, s.description, s.body) for s in self.skills
        ]
        self._search_docs += [
            _search.SearchDoc.build("agent", a.name, a.description, a.body) for a in self.agents
        ]
        self._search_docs += [
            _search.SearchDoc.build("rule", r.name, r.description or "", r.body) for r in self.rules
        ]

        self._ref_cache: dict[str, str] = {}

    # ---- existence ------------------------------------------------------- #
    def skill_exists(self, name: str) -> bool:
        return _norm(name) in self._skill_by_name

    def agent_exists(self, name: str) -> bool:
        return _norm(name) in self._agent_by_name

    def rule_exists(self, name: str) -> bool:
        return _norm(name) in self._rule_by_name

    def skill_names(self) -> list[str]:
        return [s.name for s in self.skills]

    def agent_names(self) -> list[str]:
        return [a.name for a in self.agents]

    def rule_names(self) -> list[str]:
        return [r.name for r in self.rules]

    # ---- skills ---------------------------------------------------------- #
    def list_skill_summaries(self, source: str = "all") -> list[SkillSummary]:
        source = (source or "all").lower()
        out = []
        for s in self.skills:
            if source != "all" and s.source != source:
                continue
            out.append(
                SkillSummary(
                    name=s.name,
                    description=s.description,
                    source=s.source,
                    user_invocable=s.user_invocable,
                    disable_model_invocation=s.disable_model_invocation,
                    argument_hint=s.argument_hint,
                    has_references=bool(s.references),
                    reference_filenames=[r.filename for r in s.references],
                )
            )
        return out

    def skill_detail(self, name: str) -> SkillDetail | None:
        skill = self._skill_by_name.get(_norm(name))
        if skill is None:
            return None
        return SkillDetail(
            name=skill.name,
            description=skill.description,
            source=skill.source,
            allowed_tools=list(skill.allowed_tools),
            user_invocable=skill.user_invocable,
            disable_model_invocation=skill.disable_model_invocation,
            argument_hint=skill.argument_hint,
            context=skill.context,
            agent=skill.agent,
            references=[ReferenceInfo(r.filename, r.rel_path) for r in skill.references],
            used_by_agents=list(self._agents_for_skill.get(_norm(skill.name), [])),
            body=skill.body,
        )

    def skill_reference_infos(self, name: str) -> list[ReferenceInfo] | None:
        skill = self._skill_by_name.get(_norm(name))
        if skill is None:
            return None
        return [ReferenceInfo(r.filename, r.rel_path) for r in skill.references]

    def read_skill_reference(self, name: str, filename: str) -> str | None:
        """Return a reference file's body, or None if the skill or file is unknown."""
        skill = self._skill_by_name.get(_norm(name))
        if skill is None:
            return None
        wanted = filename.strip().lower()
        for ref in skill.references:
            if wanted in (ref.filename.lower(), ref.filename.lower().removesuffix(".md")):
                return self._read_reference_body(ref.abs_path)
        return None

    def _read_reference_body(self, abs_path: str) -> str:
        if abs_path not in self._ref_cache:
            path = Path(abs_path)
            # Defense-in-depth: only ever read files inside the repo root.
            if not within_root(self.repo_root, path):
                raise PermissionError(f"refusing to read outside repo root: {abs_path}")
            self._ref_cache[abs_path] = path.read_text(encoding="utf-8")
        return self._ref_cache[abs_path]

    # ---- agents ---------------------------------------------------------- #
    def list_agent_summaries(self) -> list[AgentSummary]:
        return [
            AgentSummary(name=a.name, description=a.description, model=a.model, skills=list(a.skills))
            for a in self.agents
        ]

    def agent_detail(self, name: str) -> AgentDetail | None:
        agent = self._agent_by_name.get(_norm(name))
        if agent is None:
            return None
        resolved, unresolved = [], []
        for skill_name in agent.skills:
            skill = self._skill_by_name.get(_norm(skill_name))
            if skill is None:
                unresolved.append(skill_name)
            else:
                resolved.append(SkillRef(name=skill.name, description=skill.description))
        return AgentDetail(
            name=agent.name,
            description=agent.description,
            model=agent.model,
            skills_resolved=resolved,
            skills_unresolved=unresolved,
            body=agent.body,
        )

    # ---- rules ----------------------------------------------------------- #
    def list_rule_summaries(self, include_general: bool = True) -> list[RuleSummary]:
        return [
            RuleSummary(
                name=r.name, paths=list(r.paths), is_general=r.is_general, description=r.description
            )
            for r in self.rules
            if include_general or not r.is_general
        ]

    def rule_detail(self, name: str) -> RuleDetail | None:
        rule = self._rule_by_name.get(_norm(name))
        if rule is None:
            return None
        return RuleDetail(
            name=rule.name,
            paths=list(rule.paths),
            is_general=rule.is_general,
            description=rule.description,
            body=rule.body,
        )

    def rules_for_path(self, path: str, include_general: bool = True) -> RulesForPathResult:
        matched: list[MatchedRule] = []
        for rule in self._path_rules:
            for glob, compiled in self._rule_globs[rule.name]:
                if _search.glob_matches(compiled, path):
                    matched.append(
                        MatchedRule(
                            name=rule.name,
                            paths=list(rule.paths),
                            matched_glob=glob,
                            body=rule.body,
                        )
                    )
                    break  # first matching glob is enough
        general = (
            [GeneralRule(name=r.name, body=r.body) for r in self._general_rules]
            if include_general
            else []
        )
        return RulesForPathResult(path=path, matched=matched, general=general)

    # ---- search + overview ---------------------------------------------- #
    def search(self, query: str, kind: str = "all", limit: int = 15) -> list[SearchHit]:
        scored = _search.search(self._search_docs, query, kind=kind, limit=limit)
        return [
            SearchHit(
                kind=sd.doc.kind,
                name=sd.doc.name,
                description=sd.doc.description,
                score=round(sd.score, 2),
                matched_terms=sd.matched_terms,
            )
            for sd in scored
        ]

    def overview(self) -> CatalogOverview:
        return CatalogOverview(
            skills=len(self.skills),
            agents=len(self.agents),
            rules=len(self.rules),
            general_rules=len(self._general_rules),
            render_skills_included=self.render_skills_included,
            load_warnings=list(self.load_warnings),
        )
