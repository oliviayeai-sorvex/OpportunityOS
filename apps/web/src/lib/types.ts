export type RiskLevel = "low" | "medium" | "high";

export type Opportunity = {
  id: string;
  external_id: string;
  source: string;
  domain: string;
  title: string;
  value_estimate: number;
  risk_level: RiskLevel;
  verification_status: "pending" | "verified" | "rejected";
  score_card?: {
    total: number;
    confidence: number;
    factors: Record<string, number>;
  };
};

export type DashboardSummary = {
  total: number;
  verified: number;
  pending: number;
  rejected: number;
  by_domain: Record<string, number>;
};
