/** Workload / budget context for estimate upload (shared types & helpers). */

export type WorkloadContext = {
  system_description?: string;
  information_requirements?: string;
  monthly_budget?: string;
  budget_currency?: string;
  cost_constraints?: string;
  monthly_egress_gb?: string;
  peak_bandwidth_mbps?: string;
  cross_region_traffic?: string;
  monthly_active_users?: string;
  concurrent_users?: string;
  api_requests_per_month?: string;
  storage_hot_gb?: string;
  storage_backup_gb?: string;
  availability_sla?: string;
  primary_regions?: string;
  environment?: string;
  growth_pct_year?: string;
  workload_pattern?: string;
};

export const EMPTY_WORKLOAD_CONTEXT: WorkloadContext = {
  system_description: '',
  information_requirements: '',
  monthly_budget: '',
  budget_currency: 'USD',
  cost_constraints: '',
  monthly_egress_gb: '',
  peak_bandwidth_mbps: '',
  cross_region_traffic: '',
  monthly_active_users: '',
  concurrent_users: '',
  api_requests_per_month: '',
  storage_hot_gb: '',
  storage_backup_gb: '',
  availability_sla: '',
  primary_regions: '',
  environment: '',
  growth_pct_year: '',
  workload_pattern: '',
};

/** Build JSON for upload FormData; omit empty fields. */
export function serializeWorkloadContext(ctx: WorkloadContext): string | null {
  const out: Record<string, string | number> = {};
  for (const [key, raw] of Object.entries(ctx)) {
    const text = (raw ?? '').trim();
    if (!text) continue;
    if (
      [
        'monthly_budget',
        'monthly_egress_gb',
        'peak_bandwidth_mbps',
        'monthly_active_users',
        'concurrent_users',
        'api_requests_per_month',
        'storage_hot_gb',
        'storage_backup_gb',
        'growth_pct_year',
      ].includes(key)
    ) {
      const n = Number(text);
      if (!Number.isFinite(n) || n < 0) continue;
      out[key] = n;
    } else {
      out[key] = text;
    }
  }
  return Object.keys(out).length ? JSON.stringify(out) : null;
}
