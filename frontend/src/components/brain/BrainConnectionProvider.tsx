import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { useBrainConnection } from '../../brain/useBrainConnection';
import { isEntryPagePath, pageForPath } from '../../brain/brainRoutePage';
import { BrainAssistantContext, type BrainAssistantValue } from '../../brain/brainAssistant';
import { BrainSession } from './BrainSession';

/**
 * BrainConnectionProvider — 全站唯一的大腦連線與浮動小助手狀態（部署後追加「全站大腦小助手」，2026-11-15）
 *
 * 掛在 `BrowserRouter` 之內、`Routes` 之外：換頁不重掛，所以連線、小助手的展開狀態與草稿都跨頁保留。
 * `page` 由目前路由推導（`pageForPath`，唯一對應處）；`enabled` 為 `K1 view`——沒有 K1 不開連線，與原本各頁
 * 「`brainEnabled = can('K1', 'view')` 才開」相同。入口頁、工作區、評估頁、專案頁不再各自呼叫
 * `useBrainConnection`，改以 `useBrainSession()` 取得這一條。`BrainSession` 也只在這裡掛一次，全站只有
 * 一個大腦 `LiveRegion`（`BR98.3`）。
 */
export const BrainConnectionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { pathname } = useLocation();
  const { can, subscribeAuthBoundary } = useAuth();
  const connection = useBrainConnection(pageForPath(pathname), {
    enabled: can('K1', 'view'),
    assistantSurface: !isEntryPagePath(pathname),
  });

  const [open, setOpenState] = useState(false);
  const [draft, setDraft] = useState('');
  const [seenReplyCount, setSeenReplyCount] = useState(0);
  const replyCount = connection.assistantReplyCount;
  const replyCountRef = useRef(replyCount);
  useEffect(() => {
    replyCountRef.current = replyCount;
  });

  // 換人即清空草稿、收合並把既有回覆記為已讀（與對話紀錄同一個身分邊界事件；setState 在訂閱回呼內，
  // 不在 effect body）。回覆數是連線層的累計值，不隨換人歸零，所以已讀點要對齊到當下的值。
  useEffect(
    () =>
      subscribeAuthBoundary(() => {
        setOpenState(false);
        setDraft('');
        setSeenReplyCount(replyCountRef.current);
      }),
    [subscribeAuthBoundary],
  );

  const setOpen = useCallback(
    (next: boolean) => {
      setOpenState(next);
      setSeenReplyCount(replyCount);
    },
    [replyCount],
  );

  const assistant = useMemo<BrainAssistantValue>(
    () => ({ open, setOpen, draft, setDraft, unread: !open && replyCount > seenReplyCount }),
    [open, setOpen, draft, replyCount, seenReplyCount],
  );

  return (
    <BrainSession connection={connection}>
      <BrainAssistantContext.Provider value={assistant}>{children}</BrainAssistantContext.Provider>
    </BrainSession>
  );
};
