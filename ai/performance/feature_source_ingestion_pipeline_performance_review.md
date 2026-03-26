# Performance Review: source_ingestion_pipeline

## Load Assumptions
- DAU: 100 operators
- Peak CCU: 25
- Peak ingestion trigger rate: 10 runs/minute
- Read/write mix: read-heavy dashboard, bursty writes during ingestion.

## Bottleneck Analysis
- Database: Upsert path depends on `(external_id, source)` index; missing index causes write amplification.
- Compute: Adapter normalization is lightweight; scoring is O(n) per record and CPU-cheap.
- I/O: External provider latency dominates p95; use bounded retries and parallel provider execution.

## Scaling Risks
- SPOF risk if ingestion runs only on one worker process.
- Connection pool saturation possible under concurrent ingestion + dashboard reads.
- Recommendation: independent worker autoscaling and queue-backed ingestion jobs.

## Query Optimization
- Use cursor pagination for opportunity listing when rows > 10k.
- Cache dashboard aggregates for short TTL (15-30s).
- Archive stale opportunities beyond retention threshold to reduce hot-table scans.
