/**
 * useAssessmentTargetSync — `/assessment` 與作業對象的雙向同步掛點（`BR97.5`、`BR97.6`）
 *
 * 判斷與 `/workspace` 共用：核心 `useTargetSyncCore` 與純函式 `decideInitialAlignment` 皆在
 * `useWorkspaceTargetSync.ts`（`NFR2.141`：快照先到、後到由同一份判斷承載）。本頁差異只在輸入：
 * 選定的圖＝`diagramOverride ?? urlDiagramId`（網址參數優先，`BR97.5` (1)）；未儲存內容＝
 * `hasUnsavedAssessmentWork(uploadedXml, optimizeDraft)`（security-design §六之三）；就緒＝圖清單請求已結束。
 */

import type { BrainConnection } from './brainSession';
import { useTargetSyncCore, type OwnedDiagram, type TargetSync } from './useWorkspaceTargetSync';
import { hasUnsavedAssessmentWork } from '../utils/unsavedWork';

interface AssessmentSyncInput {
  selectedDiagramId: number | null;
  urlDiagramId: number | null;
  diagrams: readonly OwnedDiagram[];
  uploadedXml: string | null;
  optimizeDraft: unknown;
  openDiagram: (id: number) => void;
}

export function useAssessmentTargetSync(conn: BrainConnection, input: AssessmentSyncInput): TargetSync {
  return useTargetSyncCore(conn, {
    currentDiagramId: input.selectedDiagramId,
    urlDiagramId: input.urlDiagramId,
    diagrams: input.diagrams,
    unsaved: hasUnsavedAssessmentWork(input.uploadedXml, input.optimizeDraft),
    unsavedCanvas: input.selectedDiagramId === null && input.uploadedXml !== null,
    openDiagram: input.openDiagram,
  });
}
