import type { DashboardSummary, Opportunity } from "./types";

const demoRows: Opportunity[] = [
  {
    id: "1",
    external_id: "stk-001",
    source: "stocks",
    domain: "stocks",
    title: "Undervalued semiconductor basket",
    value_estimate: 920000,
    risk_level: "medium",
    verification_status: "pending",
    score_card: { total: 79.2, confidence: 0.83, factors: { value: 0.61, risk: 0.75 } },
  },
  {
    id: "2",
    external_id: "re-441",
    source: "real_estate",
    domain: "real_estate",
    title: "Distressed multifamily acquisition",
    value_estimate: 1500000,
    risk_level: "low",
    verification_status: "verified",
    score_card: { total: 92.3, confidence: 0.95, factors: { value: 1.0, risk: 1.0 } },
  },
];

export async function fetchDashboardData(): Promise<{ summary: DashboardSummary; items: Opportunity[] }> {
  const summary: DashboardSummary = {
    total: demoRows.length,
    verified: demoRows.filter((r) => r.verification_status === "verified").length,
    pending: demoRows.filter((r) => r.verification_status === "pending").length,
    rejected: demoRows.filter((r) => r.verification_status === "rejected").length,
    by_domain: {
      stocks: demoRows.filter((r) => r.domain === "stocks").length,
      real_estate: demoRows.filter((r) => r.domain === "real_estate").length,
      grants: demoRows.filter((r) => r.domain === "grants").length,
    },
  };
  return Promise.resolve({ summary, items: demoRows });
}
