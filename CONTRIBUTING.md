# Contributing to Sonic-Celestial

Welcome! This document covers everything you need to get started — setting up your local environment, running the app, and contributing features using the AI-driven engineering workflow.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker | >= 24 | [docker.com](https://www.docker.com) |
| Docker Compose | >= 2.20 | Included with Docker Desktop |
| Python | >= 3.11 | [python.org](https://www.python.org) |
| Node.js | >= 20 | [nodejs.org](https://nodejs.org) |
| npm | >= 10 | Included with Node.js |

---

## Local Setup

### 1. Clone and Configure

```bash
git clone <repo-url>
cd sonic-celestial

# Copy and configure backend env vars
cp apps/control-plane/.env.example apps/control-plane/.env
# Edit apps/control-plane/.env with real local values

# Copy and configure frontend env vars
cp apps/web/.env.example apps/web/.env.local
```

### 2. Start the Full Stack

```bash
docker-compose up
```

This starts:
- **API** at `http://localhost:8000`
- **Web app** at `http://localhost:3000`
- **PostgreSQL** at `localhost:5432`
- **Redis** at `localhost:6379`

### 3. Run Database Migrations

```bash
docker-compose exec api alembic upgrade head
```

---

## Running Tests

See [`tests/README.md`](./tests/README.md) for full details.

```bash
# Backend unit tests (fast, no DB needed)
pytest tests/unit/

# Backend integration tests (requires DB)
docker-compose up db -d
pytest tests/integration/

# Full E2E tests (requires everything running)
docker-compose up -d
pytest tests/e2e/
docker-compose down
```

---

## Contributing a New Feature

This project uses the **Feature Autopilot** AI engineering workflow (see `SKILL.md`).

### If starting a brand new product:
```
/plan-mvp
```
This fills out `docs/mvp_scope.md` and `ai/architecture/system_architecture.md`, then creates feature stubs in `ai/tasks/`.

### If building an individual feature:
```
/build-feature {feature_name}
```
This runs the full Part 0–5 lifecycle: PM spec → UX → Architecture → Implementation → QA → Completion summary.

### Other commands:
```
/review-security {name}   ← Scoped security review for a feature
/run-qa {name}            ← QA Validation + Performance review
```

---

## Project Structure

```
sonic-celestial/
├── SKILL.md                  ← Agent entry point & persona definitions
├── process.md                ← Full engineering lifecycle (Part -1 to Part 5)
├── observability.md          ← Logging, tracing & alerting standards
├── performance.md            ← Performance & scalability checklist
├── qa.md                     ← Feature status tracker (all features, all parts)
├── docker-compose.yml        ← Local development environment
│
├── .agents/workflows/        ← Slash command triggers for the AI workflow
│
├── ai/
│   ├── tasks/                ← Feature spec inbox (feature_{name}.md)
│   ├── architecture/         ← Per-feature + system architecture docs
│   ├── security/             ← Per-feature security reviews
│   ├── observability/        ← Per-feature observability plans
│   ├── performance/          ← Per-feature performance reviews
│   └── context/              ← Feature completion summaries
│
├── apps/
│   ├── control-plane/        ← Backend (Python / FastAPI)
│   │   └── src/
│   │       ├── api/          ← Route handlers (thin layer)
│   │       ├── services/     ← Business logic (thick layer)
│   │       ├── models/       ← Data models (SQLAlchemy / Pydantic)
│   │       ├── adapters/     ← External service integrations
│   │       └── workers/      ← Async background jobs
│   └── web/                  ← Frontend (React / TypeScript)
│       └── src/
│           ├── components/
│           ├── pages/
│           ├── hooks/
│           └── lib/
│
├── docs/
│   ├── mvp_scope.md          ← Product vision & feature list (Part -1)
│   └── ux/                   ← Per-feature UX & UI component docs
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## Code Style

- **Backend**: Follow PEP 8. Use type hints everywhere. Run `ruff` for linting.
- **Frontend**: Follow the ESLint config. Functional components only. TypeScript strict mode.
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `chore:`.

---

## Questions?

Check `SKILL.md` to understand the AI agent workflow, or `process.md` for the full engineering lifecycle. If in doubt, run `/plan-mvp` to start fresh.
