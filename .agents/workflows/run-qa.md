---
description: Run QA validation and performance review for a specific feature
---

# /run-qa Workflow

**Usage**: `/run-qa {name}` — runs Part 4 (QA Validation & Performance) for a named feature.

**Prerequisites**: Part 3 (Implementation) must be complete. Tests must exist in `tests/unit/`, `tests/integration/`, and `tests/e2e/`.

## Steps

1. Read `process.md` Part 4 in full.
2. Read `performance.md` performance checklist.
3. Read `ai/architecture/feature_{name}_architecture.md` to understand what's being tested.
4. Adopt the **QA Engineer** persona.

### QA Validation
5. Run unit tests: `pytest tests/unit/` (or `npm test` for frontend).
6. Run integration tests: `pytest tests/integration/` — requires DB + env vars from `.env.example`.
7. Run e2e tests: `pytest tests/e2e/` — requires full stack running via `docker-compose up`.
8. For each failing test: identify the root cause, fix the implementation, and re-run.
9. Simulate the full client request flow end-to-end (Gateway → Router → Provider → Logging → Policy Engine).
10. Validate all acceptance criteria from `ai/tasks/feature_{name}.md` are met.

### Performance Review
11. Adopt the **Performance Engineer** persona.
12. Using `performance.md` as a checklist, analyze:
    - Load assumptions (DAU, CCU, QPS)
    - Database query efficiency (indexes, N+1, table locks)
    - Caching opportunities
    - Async I/O compliance (no blocking calls)
    - Horizontal scalability
    - Single points of failure
13. Write `ai/performance/feature_{name}_performance_review.md` with findings and recommendations.

### Sign-off
14. Update `qa.md` — set Part 4 to ✅.
15. Report: test pass/fail summary, any performance risks, and whether the feature is ready for Part 5.
