import React from 'react';

/**
 * MemorySummaryTab — 記憶摘要籤（`BR86.3`、`OPEN-PP23-3`）
 *
 * **誠實宣告，不發任何請求**：專案記憶的彙整管道（誰觸發、多久一次、摘要由誰做、
 * 摘要後的可見範圍）沒有任何上游定義，記憶的可見範圍也沒有「專案」這一級。
 * **不得以 `/api/memory/*` 的個人記憶冒充專案彙整**——那會把非本專案的內容放在專案頁上。
 */
export const MemorySummaryTab: React.FC = () => (
  <div data-testid="memory-summary-unavailable" className="space-y-2 rounded-xl border border-gray-100 p-6">
    <p className="text-sm text-gray-700">專案記憶的彙整尚未提供。</p>
    <p className="text-sm text-gray-600">
      <span aria-hidden="true">(i) </span>
      這裡將是唯讀的彙整結果。要改內容請到各功能頁，或在入口頁直接說。
    </p>
  </div>
);
