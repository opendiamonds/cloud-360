/** Shapes mirrored from the U1 `/api/iac` contract. The UI does not invent fields. */

export type RunStatus = 'succeeded' | 'failed';

export type Severity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type MaxSeverity = 'NONE' | Severity;

export type IacAction = 'generate' | 'scan' | 'rewrite' | 'download' | 'session';

export type IacStep = 'generate' | 'scan' | 'secrets';

export interface IacFileEntry {
  path: string;
  content: string;
}

export interface DraftSummary {
  draft_id: string;
  diagram_id: number;
  status: RunStatus;
  module_tree: { files: IacFileEntry[] };
  created_at: string;
}

export interface Finding {
  id: string;
  severity: Severity;
  title: string;
  detail?: string | null;
  path?: string | null;
}

export type CheckStatus = 'passed' | 'failed' | 'skipped';

export interface CheckItem {
  id: string;
  title: string;
  status: CheckStatus;
  path?: string | null;
  resource?: string | null;
}

export interface ScanReport {
  report_id: string;
  draft_id: string;
  diagram_id: number;
  status: RunStatus;
  findings: Finding[];
  max_severity: MaxSeverity;
  created_at: string;
  checks?: CheckItem[];
}

export interface RewriteResult {
  rewrite_id: string;
  draft_id: string;
  report_id: string;
  status: RunStatus;
  rewritten_paths: string[];
  created_at: string;
}

export interface SessionSnapshot {
  diagram_id: number;
  draft?: DraftSummary | null;
  latest_scan?: ScanReport | null;
  latest_rewrite?: RewriteResult | null;
  advice?: string | null;
  scan_advice?: string | null;
}

export interface DiagramOption {
  id: number;
  title: string;
}

export type DiagramReadinessStatus = 'ready' | 'empty' | 'unreadable';

export interface DiagramReadiness {
  diagram_id: number;
  title: string;
  status: DiagramReadinessStatus;
  node_count: number;
}

export interface IacUiError {
  action: IacAction;
  code: string;
  text: string;
}
