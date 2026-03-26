# Secrets Management Standard

> **Reference this document during Part 2, Step 2 (Security Review)** to ensure all features comply with secrets handling standards.

---

## 1. Categories of Secrets

| Category | Examples | Sensitivity |
|----------|---------|-------------|
| Infrastructure | DB passwords, Redis auth, JWT secret keys | 🔴 Critical |
| Third-party API Keys | OpenAI key, Anthropic key, Stripe key | 🔴 Critical |
| Internal Service Tokens | Service-to-service auth tokens | 🟠 High |
| Configuration Values | Feature flags, model names | 🟢 Low |

---

## 2. How Secrets Are Injected

**Rule**: Secrets are ONLY injected via **environment variables**. They are NEVER:
- Hardcoded in source code
- Committed to version control (`.env` is in `.gitignore`)
- Passed as CLI arguments
- Stored in database columns in plaintext

### Local Development
```bash
cp apps/control-plane/.env.example apps/control-plane/.env
# Fill in real values in .env — this file is gitignored
```

### Staging / Production
- Secrets are managed by a secrets manager (e.g. AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault).
- CI/CD pipelines inject secrets as environment variables at runtime.
- No secrets are stored in the repository or Docker images.

---

## 3. Accessing Secrets in Code

Secrets must be accessed through a central config module, never via raw `os.environ` in business logic:

```python
# ✅ Correct — use the config module
from src.config import settings
api_key = settings.OPENAI_API_KEY

# ❌ Wrong — never do this in services or adapters
import os
api_key = os.environ["OPENAI_API_KEY"]
```

The config module (`src/config.py`) validates all required secrets at startup and fails fast if any are missing.

---

## 4. Secret Rotation Policy

| Secret Type | Rotation Frequency | Who Owns It |
|-------------|-------------------|-------------|
| JWT Secret Key | Every 90 days | Platform team |
| DB Password | Every 90 days | Platform team |
| LLM API Keys | On compromise or every 180 days | Engineering lead |
| Internal tokens | On team member offboarding | Platform team |

---

## 5. What Must NEVER Be Logged

**Rule**: Structured logs (see `observability.md`) must NEVER contain:

- API keys or tokens
- Passwords or hashes
- Full credit card or payment data
- SSNs, government IDs, or other PII fields
- JWT payloads (headers are OK, payload is not)

Use a **redaction middleware** at the logging layer to strip known secret patterns from all log output.

---

## 6. Security Review Checklist (for feature security docs)

When writing `ai/security/feature_{name}_security.md`, verify:

- [ ] No secrets hardcoded in source or config files
- [ ] All secrets accessed via the central config module
- [ ] No secrets appear in logs (verify with log grep)
- [ ] API keys are scoped to minimum required permissions
- [ ] LLM API calls do not pass raw user PII in prompt context without redaction
- [ ] `.env.example` is updated if a new env var is introduced by this feature
