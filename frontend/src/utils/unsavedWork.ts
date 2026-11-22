/**
 * unsavedWork.ts — 「頁面有未儲存內容」的唯一判定（security-design §六之三；`EPN-18`）
 *
 * 純函式、無 React 依賴。判定只有一份：`WorkspacePage.handleCanvasExit` 的離開確認與大腦同步掛點的
 * 「不自動開圖」（functional-design R-02、nfr-requirements R-06）共用同一個式子，下一個改判定的人
 * 只需改一處。
 */

import type { DiagramSaveStatus } from '../components/DrawioCanvas';

/**
 * 由 `WorkspacePage.tsx` 的 `handleCanvasExit` **原樣抽出**：no-file 但畫布已有 XML（例如 AI 剛產圖
 * 尚未建檔）也視為有未儲存內容。
 */
export function isCanvasDirty(saveStatus: DiagramSaveStatus, xml: string): boolean {
  return (
    saveStatus === 'unsaved' ||
    saveStatus === 'saving' ||
    (saveStatus === 'no-file' && !!xml.trim())
  );
}

/** 評核頁：已上傳但尚未存成圖的 `.drawio`，或尚未存回的優化草稿。 */
export function hasUnsavedAssessmentWork(uploadedXml: string | null, optimizeDraft: unknown): boolean {
  return uploadedXml !== null || optimizeDraft !== null;
}
