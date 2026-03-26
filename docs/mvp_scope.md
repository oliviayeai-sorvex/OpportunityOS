# MVP Scope: OpportunityOS

## 1. Product Vision

**One-liner**: OpportunityOS continuously discovers and ranks high-value stock, real-estate, and grant opportunities so operators can act quickly from one verification dashboard.

**Problem Statement**:
Opportunity discovery is fragmented across data providers and manual research workflows. Teams lose opportunities because they cannot normalize, compare, and prioritize opportunities fast enough.

**Solution Summary**:
OpportunityOS ingests multi-source signals, normalizes them into a unified opportunity model, computes configurable scores, and surfaces explainable ranked opportunities in an operator dashboard with verification status.

## 2. Target Users

| User Type | Description | Primary Need |
|-----------|-------------|--------------|
| Primary   | Investment operators and analysts | Discover and verify top opportunities quickly with clear rationale |
| Secondary | Portfolio managers and principals | View pipeline quality, conversion, and risk posture from dashboard metrics |

## 3. Success Metrics

| Metric | MVP Target | 3-Month Target |
|--------|-----------|----------------|
| Time from signal ingestion to scored opportunity | < 2 minutes p95 | < 45 seconds p95 |
| Weekly qualified opportunities surfaced | >= 50 | >= 200 |
| Operator verification throughput | >= 20/day | >= 75/day |
| False-positive rate (operator-rejected) | <= 35% | <= 20% |

## 4. Feature List

| Priority | Feature Name | Description | Notes |
|----------|-------------|-------------|-------|
| P0 (Must Have) | source_ingestion_pipeline | Ingest and normalize stocks, real estate, and grants from pluggable provider adapters | Must support scalable connector onboarding |
| P0 (Must Have) | opportunity_command_center | Score, filter, rank, and verify opportunities in a single dashboard view | Dashboard must expose verifiable scoring signals |
| P1 (Should Have) | action_queue_watchlist | Operator watchlists, saved filters, and action queue for follow-up workflows | Improves operator execution speed |
| P2 (Nice to Have) | automated_outreach_and_bidding | Trigger outreach or application drafts for selected opportunities | Post-MVP automation |

**Priority Definitions:**
- **P0**: MVP is not shippable without this.
- **P1**: Strongly desired for MVP but can be cut if timeline is at risk.
- **P2**: Post-MVP enhancements.

## 5. Out of Scope (MVP)

- [x] Native mobile app
- [x] Auto-submission of legal contracts or grant filings
- [x] Fully autonomous trade execution

## 6. Key Constraints & Assumptions

- **Timeline**: 8-10 weeks for MVP
- **Team Size**: 1-2 engineers + 1 operator stakeholder
- **Tech Stack**: Python backend services, TypeScript React frontend, PostgreSQL, Redis-compatible cache abstraction
- **Key Assumptions**: External data providers have stable APIs; operators define filter criteria per opportunity type; compliance policy review occurs before production launch.

## Approval

- [x] User has reviewed and approved this MVP scope (autonomous `/run-agent` mode)
- [x] System architecture design may proceed (`ai/architecture/system_architecture.md`)
