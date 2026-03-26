# Performance Standard

This document outlines the standard performance checkpoints and scalability considerations that must be handled for any new feature. Use this as a guide when writing `ai/performance/feature_{name}_performance_review.md`.

## 1. Load Assumptions
- Expected Daily Active Users (DAU) and Concurrent Users (CCU).
- Expected QPS (Queries per Second) at peak.
- Data written vs Data read (read-heavy, write-heavy, mixed).

## 2. Bottleneck Analysis
- **Database**:
  - Are queries using indexes correctly?
  - Will current schema lock tables or cause degraded throughput?
  - Do we need caching (Redis/Memcached)?
- **Compute**:
  - Are the backend services CPU-bound or memory-bound?
  - Evaluate synchronous blocking I/O (must use async).

## 3. Scaling Risks
- Is there any single point of failure (SPOF)?
- Can the service be horizontally scaled cleanly behind a load balancer?
- Evaluate maximum open connections in the connection pool.

## 4. Query Optimizations
- N+1 query problems in ORMs.
- Pagination standard (Cursor vs Offset).
- Data pruning or archiving strategies for massive tables.
