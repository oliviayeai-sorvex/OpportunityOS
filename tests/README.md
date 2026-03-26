# Testing Guide

This document defines the testing philosophy, frameworks, structure, and how to run tests for this project.

---

## Philosophy

- **Test First**: Test plans are written during **Part 2 (Architecture & Planning)**  before implementation begins.
- **Layered Coverage**: Unit tests cover business logic in isolation. Integration tests cover service boundaries and DB. E2E tests simulate real end-to-end request flows.
- **Coverage Target**: Minimum **80% line coverage** for backend services. Critical paths must have E2E coverage.

---

## Test Structure

```
tests/
├── unit/           ← Individual functions and classes in isolation (no DB, no I/O)
├── integration/    ← Service-to-service and service-to-DB interactions
└── e2e/            ← Full request flow simulations (requires full stack)
```

Per-feature test files follow the naming convention:

```
tests/unit/test_feature_{name}.py
tests/integration/test_feature_{name}_integration.py
tests/e2e/test_feature_{name}_e2e.py
```

---

## Backend Tests (Python / pytest)

### Prerequisites

```bash
pip install pytest pytest-asyncio pytest-cov httpx
cp apps/control-plane/.env.example apps/control-plane/.env
# Fill in local values in .env
```

### Run Unit Tests

```bash
pytest tests/unit/ -v --cov=apps/control-plane/src --cov-report=term-missing
```

### Run Integration Tests

> Requires: local DB running. Use `docker-compose up db` or a local Postgres instance.

```bash
pytest tests/integration/ -v
```

### Run E2E Tests

> Requires: full stack running. Use `docker-compose up` to start everything.

```bash
docker-compose up -d
pytest tests/e2e/ -v
docker-compose down
```

---

## Frontend Tests (TypeScript / Vitest)

### Prerequisites

```bash
cd apps/web
npm install
```

### Run Unit Tests

```bash
cd apps/web
npm test
```

### Run with Coverage

```bash
cd apps/web
npm run test:coverage
```

---

## CI/CD

All tests run automatically on pull requests. The pipeline runs:
1. `pytest tests/unit/`
2. `pytest tests/integration/`
3. `pytest tests/e2e/` (against staging environment)

A PR cannot be merged if any tests fail or coverage drops below 80%.

---

## Writing Tests — Quick Reference

### Unit Test Template (Python)

```python
import pytest
from apps.control-plane.src.services.your_service import YourService

class TestYourService:
    def test_happy_path(self):
        result = YourService().do_thing(input="valid")
        assert result.success is True

    def test_invalid_input_raises(self):
        with pytest.raises(ValueError):
            YourService().do_thing(input=None)
```

### E2E Test Template (Python + httpx)

```python
import pytest
import httpx

BASE_URL = "http://localhost:8000"

class TestFeatureE2E:
    def test_full_request_flow(self):
        response = httpx.post(f"{BASE_URL}/api/v1/your-endpoint", json={"key": "value"})
        assert response.status_code == 200
        assert response.json()["result"] == "expected"
```
