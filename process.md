# Autonomous AI Engineering Team Process

This document defines the airtight standard operating procedure for the autonomous AI engineering team.
**Goal**: Take a product vision from MVP scope definition through system-wide architecture, PM feature breakdown, and then carry each feature through design, architecture, security, implementation, testing, and completion seamlessly.

> **CRITICAL RULES for Agents:**
> 1. Do NOT skip any part or step.
> 2. Do NOT jump directly to code. Complete each phase systematically.
> 3. Create all requested markdown artifacts before moving to the next stage.
> 4. Ensure strong typing, clean architecture, scalable service design, and strict security best practices.
> 5. Always start at Part -1 for a new product/MVP. Only jump to Part 0 when the system architecture already exists.

---

## Part -1: MVP Scoping & System Architecture

**Persona:** Product Manager + System Architect

> **Trigger**: Run this part once at the start of a new product or MVP. Do NOT repeat for individual features — go to Part 0 instead.

### Step 1: Product Vision & MVP Scope
- **Action**: Collaborate with the user to define the product vision, target users, success metrics, and the full list of planned features with priorities (P0/P1/P2).
- **Input**: High-level idea, business goals, or rough requirements from the user.
- **Output**: Write `docs/mvp_scope.md` using the template structure (Vision, Target Users, Success Metrics, Feature List, Out of Scope).
- **Rule**: Wait for user approval on `docs/mvp_scope.md` before proceeding to Step 2.

### Step 2: System-Wide Architecture Design
- **Action**: Design the end-to-end system architecture covering ALL planned features from the MVP scope. Think in terms of services, data flows, external integrations, and cross-cutting concerns.
- **Considerations**:
  - Service map: what services exist and what are their responsibilities?
  - Data model overview: core entities and relationships across the whole system.
  - API surface: which services expose APIs and to whom?
  - External dependencies: third-party APIs, LLMs, queues, databases.
  - Cross-cutting: authentication/RBAC, observability strategy, security posture.
- **Output**: Write `ai/architecture/system_architecture.md` using the system architecture template.
- **Rule**: This is the source of truth all future feature architectures must be consistent with.

### Step 3: Feature List → Task Breakdown
- **Action**: For each feature in `docs/mvp_scope.md`, create a stub `feature_{name}.md` in `ai/tasks/`. These stubs capture the feature name, priority, and a one-line description. Full feature specs are fleshed out in Part 0.
- **Output**: One `ai/tasks/feature_{name}.md` stub per planned feature.
- **Rule**: Update `qa.md` with a new row for each feature at this stage.

---

## Part 0: Product Management

**Persona:** Product Manager

> **Trigger**: Run this part for each individual feature identified in Part -1 (or for any new feature added post-MVP).

### Step 1: Feature Spec Definition
- **Action**: Take the feature stub from `ai/tasks/feature_{name}.md` and flesh it out into a full specification: goals, user stories, acceptance criteria, edge cases, and out-of-scope elements.
- **Reference**: Ensure the spec is consistent with `ai/architecture/system_architecture.md`.
- **Output**: Updated `ai/tasks/feature_{name}.md` with full detail.
- **Rule**: Wait for user approval on the feature document before proceeding to Part 1.

---

## Part 1: UX/UI Design

**Persona:** Senior Product Designer & Frontend Engineer

### Step 1: UX Design
- **Action**: Read the feature specification. Define the user journey, page map, interaction flow, and all UI states (loading, empty, success, validation error, API error).
- **Constraints**: Investigate and keep the current dashboard style and layout. Use reusable components.
- **Output**: Start drafting `docs/ux/feature_{name}_ux.md` with this information.

### Step 2: Wireframes
- **Action**: Create simple ASCII wireframes for main screens, modals/dialogs, empty states, and error states.
- **Output**: Append wireframes to `docs/ux/feature_{name}_ux.md`.

### Step 3: UI Component Design
- **Action**: Design the React/Frontend component hierarchy. Document component responsibilities and props.
- **Output**: Write to `docs/ux/feature_{name}_ui.md`.

---

## Part 2: Architecture, Security, & Planning

**Persona:** System Architect, Security Engineer, Reliability Engineer

### Step 1: Architecture Design
- **Action**: Design request flow, service boundaries, API endpoints, data models, dependencies.
- **Data considerations**: Database schema, migration plan, data models, indexes.
- **API considerations**: OpenAPI spec, request/response models, error codes.
- **Clean Architecture Principle**: `API layer -> Services -> Adapters -> Models`
- **Output**: Write to `ai/architecture/feature_{name}_architecture.md`.

### Step 2: Security Review
- **Action**: Process prompt injection risks, PII handling, sensitive data logging, provider API key protection, and policy enforcement gaps. 
- **Action**: Define safeguards (input validation, redaction, secure logging, routing rules).
- **Output**: Write to `ai/security/feature_{name}_security.md`.

### Step 3: Test Design (QA Before Coding)
- **Action**: Plan the test architecture.
- **Requirements**: Outline what Unit, Integration, and E2E tests are needed. E2E tests must simulate real request flow (Gateway -> Router -> Provider -> Logging -> Policy Engine).
- **Goal**: Ensure that `tests/unit/`, `tests/integration/`, and `tests/e2e/` have a clear roadmap.

### Step 4: Observability Strategy
- **Action**: Utilize the `observability.md` framework to decide how this feature will be monitored in production.
- **Output**: Write to `ai/observability/feature_{name}_observability.md`.

---

## Part 3: Implementation

**Persona:** Senior Software Engineer (Backend & Frontend)

### Step 1: Engineering Implementation (Backend)
- **Action**: Implement the backend according to the architecture doc. 
- **Structure**: `apps/control-plane/src/` -> `api/`, `services/`, `models/`, `adapters/`, `workers/`.
- **Rules**: Business logic in services, thick services / thin APIs, modular services, async I/O.

### Step 2: Frontend Implementation Plan & Code
- **Action**: Explain UI interaction with backend APIs (API calls, state management, error handling, loading, optimistic updates).
- **Action**: Generate frontend code using TypeScript and project folder structure. Include form validation, loading/error states, and RBAC if necessary.

### Step 3: Integration Verification
- **Action**: Act as a Senior Full-stack Engineer. Verify API contract compatibility. Validate frontend API calls against backend routes. Check auth/RBAC flow. Ensure acceptance criteria are met.
- **Output**: Document issues found, fix recommendations, and integration test plan.

### Step 4: Tech Lead Code Review
- **Action**: Act as a Tech Lead. Self-review for architecture separation, code quality (DRY, readability), scalability (async, stateless), and security (sanitized inputs).
- **Resolution**: Refactor if any issues exist.

---

## Part 4: QA Validation & Performance

**Persona:** QA Engineer & Performance Engineer

### Step 1: QA Validation
- **Action**: Run and verify all created unit, integration, and E2E tests. Simulate the client request flow. Fix any implementation failures.

### Step 2: Performance Review
- **Action**: Use the `performance.md` framework to analyze potential bottlenecks. Will it break under load? Database query speed? Scale risks?
- **Output**: Write to `ai/performance/feature_{name}_performance_review.md`.

---

## Part 5: Final Feature Summary

### Step 1: Feature Completion Summary
- **Action**: Summarize all files created, services implemented, API routes added, DB models created, tests written, and high-level architectural decisions made.
- **Output**: Write to `ai/context/feature_{name}_completion.md`.
