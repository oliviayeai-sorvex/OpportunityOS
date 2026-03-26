---
description: Run the full Part 0–5 feature lifecycle for a single feature
---

# /build-feature Workflow

**Usage**: `/build-feature {name}` — where `{name}` matches the `feature_{name}.md` stub in `ai/tasks/`.

**Prerequisites**: `/plan-mvp` must have been run. `ai/tasks/feature_{name}.md` stub must exist. `ai/architecture/system_architecture.md` must be approved.

## Steps

1. Read `process.md` Parts 0 through 5 in full.
2. Read `ai/tasks/feature_{name}.md` (the feature stub).
3. Read `ai/architecture/system_architecture.md` to understand the system context.
4. Update `qa.md` — set the feature row's Part 0 column to 🔄.

### Part 0 — PM Feature Spec
5. Adopt the **Product Manager** persona.
6. Flesh out `ai/tasks/feature_{name}.md` with full user stories, acceptance criteria, edge cases, and out of scope.
7. Wait for user approval on the feature spec before proceeding.
8. Update `qa.md` — set Part 0 to ✅, Part 1 to 🔄.

### Part 1 — UX/UI Design
9. Adopt the **Senior Product Designer & Frontend Engineer** persona.
10. Write `docs/ux/feature_{name}_ux.md` (user journey, page map, interaction flows, UI states, ASCII wireframes).
11. Write `docs/ux/feature_{name}_ui.md` (React component hierarchy, props, responsibilities).
12. Update `qa.md` — set Part 1 to ✅, Part 2 to 🔄.

### Part 2 — Architecture, Security & Planning
13. Adopt the **System Architect, Security Engineer, Reliability Engineer** personas.
14. Write `ai/architecture/feature_{name}_architecture.md` — ensure consistency with `system_architecture.md`.
15. Write `ai/security/feature_{name}_security.md`.
16. Write `ai/observability/feature_{name}_observability.md` using `observability.md` as guide.
17. Document the test plan (unit, integration, e2e outline) within the architecture doc.
18. Update `qa.md` — set Part 2 to ✅, Part 3 to 🔄.

### Part 3 — Implementation
19. Adopt the **Senior Software Engineer (Backend & Frontend)** persona.
20. Implement backend in `apps/control-plane/src/` following the Clean Architecture layers.
21. Implement frontend in `apps/web/src/` following the component hierarchy from Part 1.
22. Perform Tech Lead Code Review — self-review for DRY, security, scalability. Refactor if needed.
23. Update `qa.md` — set Part 3 to ✅, Part 4 to 🔄.

### Part 4 — QA & Performance
24. Adopt the **QA Engineer & Performance Engineer** personas.
25. Run `/run-qa {name}` (or continue inline).
26. Update `qa.md` — set Part 4 to ✅, Part 5 to 🔄.

### Part 5 — Feature Completion Summary
27. Write `ai/context/feature_{name}_completion.md` listing all files, routes, models, tests, and decisions.
28. Update `qa.md` — set Part 5 to ✅, Status to ✅ Done. Link the completion doc.
29. Report a summary to the user.
