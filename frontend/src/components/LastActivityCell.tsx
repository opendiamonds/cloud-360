import React from 'react';

interface LastActivityCellProps {
  /** ISO 8601 UTC 時間字串；null 表示從未活動 */
  lastActivityAt: string | null;
  /**
   * 是否逾期。**由呼叫端傳入，元件不自行計算** —— 「距今超過 90 天」需要當下
   * 時間，而在 render 或 useMemo 內取用當下時間會觸發既有的渲染純度 lint 規則。
   * 判定因此放在資料處理階段，也讓它成為可單元測試的純函式（後端已計算並帶出）。
   */
  isOverdue: boolean;
}

/**
 * 把後端的 UTC 時間戳顯示為 `YYYY-MM-DD HH:MM`。
 *
 * **在地化策略**：換算為使用者的本地時區後再格式化。直接截斷 ISO 字串會讓顯示
 * 時間整體偏移一個時區位移量（AC-1.6 直接失敗）—— 後端一律回 UTC，顯示端負責
 * 在地化。輸出格式由本函式手動組成，避免不同瀏覽器／ICU locale 資料導致分隔符
 * 或空白字元不一致。
 */
function formatLocal(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad2 = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

/**
 * 使用者清單中單一帳號的最後活動時間（C-5）。
 *
 * 三個狀態：有紀錄未逾期、有紀錄已逾期、無紀錄。**沒有 loading 與 error 態** ——
 * 那兩者由頁面層整塊替換整個表格處理，本元件不會在那時被渲染。
 */
export const LastActivityCell: React.FC<LastActivityCellProps> = ({
  lastActivityAt,
  isOverdue,
}) => {
  if (lastActivityAt === null) {
    // 無紀錄態：可聚焦的破折號 + 說明。與「角色」欄的破折號在**可及性層面**
    // 可區分（那個是純文字、不可聚焦、無說明），視覺維持一致。
    return (
      <span
        tabIndex={0}
        aria-label="尚無活動紀錄"
        title="尚無活動紀錄"
        className="text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400 rounded"
      >
        —
      </span>
    );
  }

  if (isOverdue) {
    // 逾期態：圖示 + 文字替代承擔主要語意，顏色為**輔助**訊號（WCAG 1.4.1 的
    // 非色彩傳達要求 —— 灰階或螢幕閱讀器下仍須可辨識）。
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-300">
        <span aria-hidden="true">(!)</span>
        <span className="sr-only">已超過 90 天未活動</span>
        <span>{formatLocal(lastActivityAt)}</span>
      </span>
    );
  }

  return <span className="text-xs text-slate-300">{formatLocal(lastActivityAt)}</span>;
};
