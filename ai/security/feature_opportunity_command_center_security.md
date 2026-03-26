# Security Review: opportunity_command_center

## Threats
- Filter injection via malformed query parameters.
- Unauthorized verification status changes.
- Leakage of sensitive opportunity notes in logs.

## Controls
- Strict typed filter parsing with default bounds.
- RBAC enforcement for verification mutation endpoints.
- Structured logging excludes free-form private notes.
- Verification reason length limits and safe string normalization.

## Secrets Checklist
- [x] No secret access from UI components.
- [x] No provider/API keys returned in dashboard responses.
- [x] Centralized env-based config only.
- [x] Redaction policy applied to request logs.
