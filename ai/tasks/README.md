# ai/tasks — Feature Specifications Inbox

This folder is the **inbox for input feature specifications**. It is the handoff point between Part -1 (MVP Scoping) and Part 0 (Product Management).

---

## Lifecycle of a Feature Spec

```
Part -1  →  Stub created here (name + priority + one-liner)
Part 0   →  PM Agent fleshes out the full spec (user stories, acceptance criteria, edge cases)
Part 1+  →  Spec referenced by UX, Architecture, Security, QA agents
Part 5   →  Completion summary written to ai/context/feature_{name}_completion.md
```

---

## File Naming Convention

```
feature_{name}.md
```

Use `snake_case` for the name. The `{name}` must be consistent across ALL artifacts:

| Artifact | Path |
|----------|------|
| Feature Spec | `ai/tasks/feature_{name}.md` |
| UX Design | `docs/ux/feature_{name}_ux.md` |
| UI Components | `docs/ux/feature_{name}_ui.md` |
| Architecture | `ai/architecture/feature_{name}_architecture.md` |
| Security | `ai/security/feature_{name}_security.md` |
| Observability | `ai/observability/feature_{name}_observability.md` |
| Performance | `ai/performance/feature_{name}_performance_review.md` |
| Completion | `ai/context/feature_{name}_completion.md` |

---

## Feature Spec Template

When creating a new feature spec (Part 0), use this structure:

```markdown
# Feature: {Name}

**Priority**: P0 / P1 / P2
**Status**: Draft / Approved / In Progress / Done

## Goal
One sentence: what does this feature accomplish for the user?

## User Stories
- As a [user type], I want to [action] so that [benefit].

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Edge Cases & Error States
- What happens if...

## Out of Scope
- Explicitly list what this feature does NOT cover.

## Dependencies
- Other features or services this depends on.
```

---

## Current Feature Stubs

> Stubs are added here by the PM Agent during Part -1, Step 3. See `qa.md` for full status.

_(No features yet — run `/plan-mvp` to get started)_
