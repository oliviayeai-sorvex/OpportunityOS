# Observability Standard

This document outlines the standard observability metrics, logs, and traces that must be defined for any new feature. Use this as a guide when writing `ai/observability/feature_{name}_observability.md`.

## 1. Metrics
- **Request Rate (RPS)**: Expected load and peak load.
- **Latency**: Sub-system latency targets (e.g. Gateway < 50ms, Provider < 1000ms).
- **Error Rates**: 4xx vs 5xx errors. Thresholds that trigger alerts.

## 2. Distributed Tracing
Each feature traversing the architecture (Gateway -> Router -> Provider -> Logging -> Policy) MUST pass a unique `x-request-id` or `trace_id`.
- Identify key span boundaries (e.g. entering adapter boundaries, external API calls).

## 3. Structured Logging
Logs must be JSON formatted and include:
- `timestamp`
- `level` (info, warn, error, debug)
- `trace_id`
- `user_id` / `tenant_id`
- `event_name`
- Avoid logging PII or secrets.

## 4. Alerts
Define what conditions should trigger an alert for the Reliability Engineer.
- Example: > 5% 5xx errors in a 5-minute tumbling window.
- Example: Provider API latency > 5s for sustained 2 minutes.
