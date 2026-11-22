/**
 * 從 Workspace 跳到 IaC 產生頁時，用 sessionStorage 記住「進頁後要立刻產生」。
 * 與 IacWorkspace 分檔：元件檔只能匯出元件（react-refresh/only-export-components）。
 */

const PENDING_GENERATE_KEY = 'iac-generate-now';

export function rememberPendingGenerate(diagramId: number) {
  sessionStorage.setItem(PENDING_GENERATE_KEY, String(diagramId));
}

export function hasPendingGenerate(diagramId: number): boolean {
  return sessionStorage.getItem(PENDING_GENERATE_KEY) === String(diagramId);
}

export function clearPendingGenerate() {
  sessionStorage.removeItem(PENDING_GENERATE_KEY);
}
