/**
 * brainSession.ts — 一個頁面的大腦連線在元件樹中的 context、型別與 hook
 *
 * Provider 元件 `BrainSession` 在 `components/brain/BrainSession.tsx`（`react-refresh/only-export-components`
 * 要求元件與非元件匯出分檔，與本檔成對）。連線本身由頁面呼叫 `useBrainConnection(page)` 持有——子頁面的
 * 同步掛點（`useWorkspaceTargetSync`／`useAssessmentTargetSync`）需要同一個連線物件。
 */

import { createContext, useContext } from 'react';
import type { BrainPage, SegmentId, SharingMode, WorkItem, WorkTargetPayload } from './brainProtocol';

export type ConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'awaiting-ready'
  | 'ready'
  | 'reconnecting'
  | 'gave-up'
  | 'needs-login'
  | 'forbidden'
  | 'version-mismatch';

/** 同步掛點向連線登記的回呼（只在事件回呼內被呼叫）。 */
export interface ConnectionListeners {
  onReady?: () => void;
  /** 本頁目前讀取段的 work_target 到達（BR92.4 已過濾）。 */
  onWorkTarget?: (payload: WorkTargetPayload) => void;
}

export interface WorkTargetIds {
  projectId: string | null;
  systemId: string | null;
  diagramId: string | null;
}

export interface BrainConnection {
  page: BrainPage;
  enabled: boolean;
  status: ConnectionStatus;
  /** 本頁目前讀取的段（入口頁恆為 shared）。 */
  readSegment: SegmentId;
  /** 子頁面的共享模式（以伺服器回推為準，BR97.3）；入口頁恆為 null。 */
  sharingMode: SharingMode | null;
  /** 本頁目前讀取段的作業對象；尚未收到為 null。 */
  target: WorkTargetPayload | null;
  workItems: WorkItem[];
  /** 已按「不是這個」、等下一則 work_items 的工作項（BR94.4）。 */
  pendingCorrections: string[];
  awaitingReply: boolean;
  /** 寫入 LiveRegion 的播報文字（BR93.6、BR98.3）。 */
  announcement: string;
  sendUserMessage: (text: string) => void;
  selectCandidate: (groupId: string, candidateId: string | null) => void;
  correctWorkItem: (workItemId: string) => void;
  setSharingMode: (mode: SharingMode) => void;
  /** 回傳是否真的送出（未 ready 時不送，nfr-design R-05）。 */
  setWorkTarget: (ids: WorkTargetIds) => boolean;
  announce: (text: string) => void;
  reconnect: () => void;
  /** 同步掛點登記事件回呼（一頁只有一個掛點）；回傳退訂函式。 */
  subscribe: (listeners: ConnectionListeners) => () => void;
}

export const BrainSessionContext = createContext<BrainConnection | undefined>(undefined);

export function useBrainSession(): BrainConnection {
  const value = useContext(BrainSessionContext);
  if (!value) throw new Error('useBrainSession must be used within a BrainSession');
  return value;
}
