/**
 * brainAssistant.ts — 浮動大腦小助手的狀態 context、型別與 hook（部署後追加「全站大腦小助手」，2026-11-15）
 *
 * Provider 是 `components/brain/BrainConnectionProvider.tsx`（`react-refresh/only-export-components`：元件與
 * 非元件匯出分檔）。狀態放在路由外層而不是小助手元件內：`Layout` 每條路由各掛一份，換頁時小助手元件會重掛，
 * 展開狀態、草稿與「已讀到第幾則」若放在元件內會隨換頁消失。只在記憶體：不寫 localStorage（對話紀錄本身也
 * 只在記憶體，`EPN-13`），重新整理即回到收合；登入／登出時清空（與對話紀錄同一個身分邊界事件）。
 */

import { createContext, useContext } from 'react';

export interface BrainAssistantValue {
  open: boolean;
  /** 展開或收合；兩者都把目前的子頁面回覆數記為已讀。 */
  setOpen: (open: boolean) => void;
  draft: string;
  setDraft: (draft: string) => void;
  /** 收合期間是否有新的大腦回覆（入口頁的回覆不算，見 `BrainConnection.assistantReplyCount`）。 */
  unread: boolean;
}

export const BrainAssistantContext = createContext<BrainAssistantValue | undefined>(undefined);

export function useBrainAssistant(): BrainAssistantValue {
  const value = useContext(BrainAssistantContext);
  if (!value) throw new Error('useBrainAssistant must be used within a BrainConnectionProvider');
  return value;
}
