import type { IacAction } from './iacTypes';

/** Short phrases keyed by `error.code`. Callers must not render the raw response body. */
const COPY: Record<string, string> = {
  missing_draft: '尚無草稿，請先產生 IaC',
  missing_scan_report: '尚無掃描報告',
  stale_report_id: '掃描報告已過期，請重新掃描',
  missing_diagram_id: '缺少架構圖',
  invalid_diagram: '架構圖無法使用',
  diagram_unreadable: '這張圖的內容無法解析，不能產生 IaC。',
  diagram_empty: '這張圖沒有可轉成 IaC 的節點。',
  diagram_mismatch: '架構圖與產物不一致',
  slot_too_large: '產物超過大小上限',
  generate_busy: '產生進行中，請稍後再試',
  generate_timeout: '產生逾時，請重試',
  generate_failed: '產生失敗，請重試',
  invalid_files: '只能修改 main.tf、variables.tf、outputs.tf。',
  scan_failed: '掃描失敗，請重試',
  rewrite_failed: '改寫失敗，請重試',
  unknown: '無法完成這項操作，請重試',
};

const FORBIDDEN: Record<IacAction, string> = {
  generate: '缺少 D1 edit 權限。',
  scan: '缺少 D2 edit 權限。',
  rewrite: '缺少 D3 edit 權限。',
  download: '缺少 D1 edit 權限。',
  session: '缺少 D1 view 權限。',
};

const TIMEOUT: Record<IacAction, string> = {
  generate: '產生逾時，請重試',
  scan: '掃描逾時，請重試',
  rewrite: '改寫逾時，請重試',
  download: '下載逾時，請重試',
  session: '工作階段讀取逾時，請重試',
};

const SCAN_REASON: Record<string, string> = {
  checkov_missing: '這台機器沒有安裝 Checkov，所以無法掃描。',
  checkov_timeout: 'Checkov 掃描逾時，請再試一次。',
  checkov_exit: 'Checkov 異常結束，沒有產出報告。',
  checkov_empty: 'Checkov 沒有回傳結果。這份草稿的資源類型可能無法被掃描。',
  checkov_unparsed: 'Checkov 的結果無法解讀。這份草稿的資源類型可能不是它認得的格式。',
};

export function mapIacErrorCode(code: string, action: IacAction, reason?: string | null): string {
  if (code === 'unauthorized') return '登入已過期，請重新登入後再產生。';
  if (code === 'forbidden') return FORBIDDEN[action];
  if (code === 'timeout') return TIMEOUT[action];
  if (code === 'scan_failed' && reason && SCAN_REASON[reason]) return SCAN_REASON[reason];
  return COPY[code] ?? COPY.unknown;
}
