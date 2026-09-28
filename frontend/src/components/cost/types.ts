/** Shared types for /api/cost/v1 estimate workspace (U8). */

export type CloudId = 'aws' | 'gcp' | 'azure';

export type EstimateLine = {
  ordinal: number;
  item_name: string | null;
  spec: string | null;
  quantity: number | null;
  amount: number | null;
  currency: string | null;
  parse_status: string;
  raw_text: string;
};

export type EstimateChecks = {
  currency_consistent: boolean;
  currency_tie: boolean;
  quantity_positive: boolean;
  total_reconciled: {
    attempted: boolean | null;
    within_tolerance: boolean | null;
    skipped_reason: string | null;
  };
  offenders: {
    currency_ordinals: number[];
    quantity_ordinals: number[];
  };
};

export type CloudEstimate = {
  cloud: CloudId;
  stated_total: number | null;
  currency: string | null;
  lines: EstimateLine[];
  checks: EstimateChecks;
};

export type EstimateSetSummary = {
  id: number;
  created_at: string | null;
  note: string | null;
  diagram_id: number | null;
  is_owner: boolean;
  is_saved: boolean;
  privacy: 'private' | 'shared' | string;
  clouds: Array<{
    cloud: CloudId;
    stated_total: number | null;
    currency: string | null;
    line_count: number;
    unparsed_count: number;
  }>;
  advice_status: string | null;
};

export type EstimateSetDetail = EstimateSetSummary & {
  estimates: CloudEstimate[];
};

export function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function cloudLabel(cloud: string): string {
  if (cloud === 'aws') return 'AWS';
  if (cloud === 'gcp') return 'GCP';
  if (cloud === 'azure') return 'Azure';
  return cloud;
}
