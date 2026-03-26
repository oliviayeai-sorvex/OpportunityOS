---
description: Plan MVP scope and system-wide architecture for a new product
---

# /plan-mvp Workflow

This workflow kicks off **Part -1** of the engineering process for a **new product or MVP**.
Run this once at the start of a new product. For individual features, use `/build-feature`.

## Steps

1. Read `process.md` Part -1 in full.
2. Read `docs/mvp_scope.md` — check if it already has content.
   - If it has content: confirm with user whether to use it as-is or update it.
   - If empty: proceed to step 3.
3. **Step 1 — MVP Scope**: Adopt the **Product Manager** persona. Ask the user for their product idea, business goals, and any known constraints. Fill out `docs/mvp_scope.md` collaboratively.
4. Present `docs/mvp_scope.md` to the user and **wait for approval** before proceeding.
5. **Step 2 — System Architecture**: Adopt the **System Architect** persona. Based on the approved MVP scope, fill out `ai/architecture/system_architecture.md`. Design the full service map, data model overview, API surface, external dependencies, and cross-cutting concerns.
6. Present `ai/architecture/system_architecture.md` to the user and **wait for approval**.
7. **Step 3 — Feature Task Breakdown**: For each P0/P1 feature in `docs/mvp_scope.md`, create a stub file `ai/tasks/feature_{name}.md` with: feature name, priority, and a one-line goal.
8. Initialize `qa.md` — add one row per feature with all status columns set to ⬜.
9. Report to the user: list all stub files created and confirm they can now use `/build-feature {name}` to begin work on individual features.
