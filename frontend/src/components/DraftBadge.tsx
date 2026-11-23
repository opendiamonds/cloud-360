import React from 'react';

/**
 * DraftBadge — 架構圖的「草稿」標示（261116-brain-create-diagram FR6.4）。
 *
 * 草稿是大腦新建、尚未完成產圖的圖；它可以被選為作業對象、接著畫，但不計入專案頁的架構圖
 * 計數、不能評核／共編／綁估價／分享（FR6.4a）。專案頁、工作區歷史清單與切換對象選單共用這一個
 * 標示，讓三處的字樣一致。純呈現，無狀態。
 */
export const DraftBadge: React.FC<{ testId: string }> = ({ testId }) => (
  <span
    data-testid={testId}
    className="rounded border border-amber-300 bg-amber-50 px-1.5 text-xs font-bold text-amber-800"
  >
    草稿
  </span>
);
