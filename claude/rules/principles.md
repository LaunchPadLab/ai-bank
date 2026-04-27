---
---

# Development Principles

- **KISS:** Prefer standard CRUD controllers, conventional routing, and Rails defaults. Add abstractions only when the current code needs them.
- **DRY is about knowledge, not shape:** Keep one authoritative representation of a business rule, but tolerate small duplication before extracting the wrong abstraction.
- **YAGNI:** Implement only what is required now. Avoid speculative flags, settings, base classes, and extension points.
- **Explicit over implicit:** Prefer named methods, explicit calls, and clear ownership over hidden callbacks or metaprogramming.
- **Composition over inheritance:** Favor concerns, delegation, and small collaborators over deep class hierarchies.
- **Decision ladder:** Use model methods for cohesive aggregate behavior; concerns for shared horizontal behavior; query objects for reusable read complexity; form objects for complex input boundaries; services for orchestration, transactions, side effects, or external systems.
- **Callbacks:** Use callbacks only for local data normalization and defaults. Side effects such as emails, API calls, job enqueueing, and related-record orchestration belong at explicit call sites or in services.
- **No premature abstraction:** Extract only after a pattern is real, repeated, and clearer when named.
