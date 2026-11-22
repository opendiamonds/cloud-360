/**
 * brainSession.ts — 全站唯一的大腦連線在元件樹中的 context、型別與 hook
 *
 * Provider 元件 `BrainSession` 在 `components/brain/BrainSession.tsx`（`react-refresh/only-export-components`
 * 要求元件與非元件匯出分檔，與本檔成對）。連線本身由 `BrainConnectionProvider`（掛在 `App.tsx` 的路由外層）
 * 呼叫 `useBrainConnection` 持有，全站一條；頁面、子頁面的同步掛點（`useWorkspaceTargetSync`／
 * `useAssessmentTargetSync`）與浮動小助手都以 `useBrainSession()` 取得同一個物件（部署後追加
 * 「全站大腦小助手」，2026-11-15）。
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
  /** 目前路由推導出的頁面種類（`brainRoutePage.pageForPath`）；送出的 user_message 帶這個值。 */
  page: BrainPage;
  /** 是否持有連線（＝使用者有 `K1 view`）。頁面與小助手的大腦掛點都以它把關。 */
  enabled: boolean;
  status: ConnectionStatus;
  /** 本頁目前讀取的段（入口頁恆為 shared）。 */
  readSegment: SegmentId;
  /** 子頁面的共享模式（以伺服器回推為準，BR97.3）；入口頁恆為 null。 */
  sharingMode: SharingMode | null;
  /** 本頁目前讀取段的作業對象；尚未收到為 null。 */
  target: WorkTargetPayload | null;
  workItems: WorkItem[];
  /** 在入口頁以外（小助手所在的畫面）終止的輪次數（done／帶輪次的 error／反問）；小助手以它判斷收合期間的未讀。 */
  assistantReplyCount: number;
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
  /**
   * 同步掛點登記事件回呼（一頁只有一個掛點）；回傳退訂函式。全站一條連線之下，換頁時快照早已到過：
   * 新掛點以 `target` 的現值取得初始作業對象（`useTargetSyncCore` 掛載時讀取），不重播事件。
   */
  subscribe: (listeners: ConnectionListeners) => () => void;
}

export const BrainSessionContext = createContext<BrainConnection | undefined>(undefined);

export function useBrainSession(): BrainConnection {
  const value = useContext(BrainSessionContext);
  if (!value) throw new Error('useBrainSession must be used within a BrainSession');
  return value;
}
