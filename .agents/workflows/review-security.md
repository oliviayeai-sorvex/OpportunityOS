---
description: Run a scoped security review for a specific feature
---

# /review-security Workflow

**Usage**: `/review-security {name}` — runs Part 2, Step 2 (Security Review) in isolation for a named feature.

**Prerequisites**: `ai/architecture/feature_{name}_architecture.md` must exist.

## Steps

1. Read `process.md` Part 2, Step 2 in full.
2. Read `ai/architecture/feature_{name}_architecture.md` to understand the feature's data flow.
3. Read `ai/architecture/system_architecture.md` for system-wide security context.
4. Read `ai/security/secrets_standard.md` for secrets management standards.
5. Adopt the **Security Engineer** persona.
6. Conduct the security review covering:
   - Prompt injection risks (if LLM-facing)
   - PII handling and redaction
   - Sensitive data logging
   - Provider API key protection
   - Input validation and sanitization
   - RBAC / policy enforcement gaps
   - Authentication flow correctness
7. Write or update `ai/security/feature_{name}_security.md` with findings, risk ratings (Critical/High/Medium/Low), and mitigations.
8. If any Critical or High findings exist — **flag immediately** and halt further implementation until resolved.
9. Report a security summary to the user with findings ranked by severity.
