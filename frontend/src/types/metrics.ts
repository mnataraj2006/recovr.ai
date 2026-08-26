export interface MetricData {
  total_revenue_at_risk: number;
  total_recovered_revenue: number;
  net_recovered_revenue: number;
  recovery_rate: number;
  transaction_recovery_rate?: number;
  revenue_recovery_rate?: number;
  at_risk_transactions?: number;
  recovered_transactions?: number;
  total_transactions?: number;
  normal_success_revenue?: number;
  total_recovery_cost: number;
  roi: number;
  nudge_count: number;
  retry_count: number;
  status_distribution: Record<string, number>;
  cause_distribution: Record<string, number>;
}

export interface SimulationHistoryItem {
  id: string;
  created_at: string;
  total_revenue_at_risk: number;
  total_recovered_revenue: number;
  recovery_rate: number;
  cohort_summary: Array<any>;
}
