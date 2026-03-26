---
description: Fully autonomous master orchestrator — runs the entire product lifecycle from idea to completion with no approval gates
---

# /run-agent Workflow

// turbo-all

This is the **fully autonomous Run Agent**. It runs the entire lifecycle — MVP scoping, system architecture, and every feature through Parts 0–5 — without pausing for approval. It reports progress at the end of each Part but never waits for input.

**Usage**: `/run-agent`

---

## How It Works

```
/run-agent
  ├─ Phase A: MVP Scope → System Architecture → Feature Stubs → qa.md
  └─ Phase B: For each feature (P0 → P1, in priority order):
        Part 0  → Part 1 → Part 2 → Part 3 → Part 4 → Part 5
  └─ Phase C: Final MVP completion report
```

---

## Steps

### PHASE A — Bootstrap (Run Once)

1. Read `SKILL.md`, `process.md`, `observability.md`, `performance.md`, `ai/security/secrets_standard.md`, and `ai/tasks/README.md` in full.
2. Check `docs/mvp_scope.md`:
   - If already filled in: use its contents as the source of truth.
   - If empty: use the product idea provided in the prompt to fill it out now.
3. Fill out `docs/mvp_scope.md` completely (Vision, Target Users, Success Metrics, Feature List with P0/P1/P2, Out of Scope).
4. Fill out `ai/architecture/system_architecture.md` completely (service map, data model, API surface, external deps, cross-cutting concerns).
5. Create one `ai/tasks/feature_{name}.md` stub per P0 and P1 feature listed in the MVP scope.
6. Initialize `qa.md` — one row per feature, all Part columns set to ⬜.
7. Report progress: *"✅ Phase A complete. MVP scope, system architecture, and [N] feature stubs created. Starting feature loop..."*

---

### PHASE B — Feature Loop (Repeat for Each Feature, P0 First)

For each feature in `qa.md`, process fully before moving to the next.

**Part 0 — PM Feature Spec**
8. Flesh out `ai/tasks/feature_{name}.md` — full user stories, acceptance criteria, edge cases, out of scope. Ensure consistency with `system_architecture.md`.
9. Update `qa.md` Part 0 → ✅. Report: *"Part 0 done for [name]."*

**Part 1 — UX/UI Design**
10. Write `docs/ux/feature_{name}_ux.md` — user journey, page map, interaction flows, all UI states (loading, empty, success, error), ASCII wireframes.
11. Write `docs/ux/feature_{name}_ui.md` — React component hierarchy, props, responsibilities.
12. Update `qa.md` Part 1 → ✅. Report: *"Part 1 done for [name]."*

**Part 2 — Architecture, Security & Planning**
13. Write `ai/architecture/feature_{name}_architecture.md` — request flow, service boundaries, API endpoints, data models, DB schema, migration plan. Must align with `system_architecture.md`.
14. Write `ai/security/feature_{name}_security.md` — prompt injection, PII handling, sensitive logging, API key protection, RBAC gaps, mitigations. Reference `secrets_standard.md`.
15. Write `ai/observability/feature_{name}_observability.md` — metrics, tracing spans, structured log events, alert conditions. Reference `observability.md`.
16. Document the test plan outline (unit, integration, e2e) within the architecture doc.
17. Update `qa.md` Part 2 → ✅. Report: *"Part 2 done for [name]."*

**Part 3 — Implementation**
18. Implement backend in `apps/control-plane/src/` following Clean Architecture: `api/ → services/ → adapters/ → models/ → workers/`. Business logic in services, thin API layer.
19. Implement frontend in `apps/web/src/` following the component hierarchy from Part 1. Include form validation, loading/error states, RBAC where needed.
20. Perform Tech Lead self-review: check architecture separation, DRY, security (sanitised inputs), async I/O compliance. Refactor immediately if anything fails.
21. Update `qa.md` Part 3 → ✅. Report: *"Part 3 done for [name]."*

**Part 4 — QA & Performance**
22. Write and run unit tests in `tests/unit/`. Fix all failures before proceeding.
23. Write and run integration tests in `tests/integration/`. Fix all failures.
24. Write and run e2e tests in `tests/e2e/` simulating full request flow. Fix all failures.
25. Verify all acceptance criteria from `ai/tasks/feature_{name}.md` are met.
26. Write `ai/performance/feature_{name}_performance_review.md` — load assumptions, DB query analysis, bottlenecks, scaling risks. Reference `performance.md`.
27. Update `qa.md` Part 4 → ✅. Report: *"Part 4 done for [name]."*

**Part 5 — Completion Summary**
28. Write `ai/context/feature_{name}_completion.md` — all files created, API routes added, DB models, tests written, key architectural decisions.
29. Update `qa.md` Part 5 → ✅, Status → ✅ Done. Link the completion doc.
30. Report: *"✅ Feature [name] complete. Moving to [next feature]..."* — loop back to step 8.

---

### PHASE C — MVP Complete

31. Once all P0 features are done, write a final summary report covering:
    - All features shipped with links to their completion docs
    - Any P1 features remaining and estimated effort
    - Unresolved performance or security notes
    - Recommended next steps for the team
32. Update `qa.md` header with overall status: **MVP P0 Complete ✅**
