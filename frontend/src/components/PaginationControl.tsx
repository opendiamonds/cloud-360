import React from 'react';

interface PaginationControlProps {
  /** 目前頁次（1 起算），取自回應 */
  page: number;
  /** 每頁筆數，**取自回應而非前端常數** —— 後端是這個值的真相來源 */
  pageSize: number;
  /** 總筆數，取自回應 */
  total: number;
  /**
   * 是否切頁中。**由呼叫端傳入**，元件不自行判斷 —— 與 LastActivityCell 的
   * isOverdue 同一形狀，理由亦同（渲染純度 lint 規則）。
   */
  isBusy: boolean;
  /** 切頁回呼；元件**不自行抓取資料** */
  onPageChange: (page: number) => void;
}

/**
 * 頁碼序列，過長時以省略號收合。回傳 `number`（可點的頁碼）與 `'…'`（佔位）。
 * 純函式、無副作用，可安全在 render 中呼叫。
 */
function pageSequence(current: number, totalPages: number): Array<number | '…'> {
  // 過渡態：刪掉某頁唯一一列後、背景重抓完成前，`page` 可能大於 `totalPages`。
  // 若不把它加進序列，就沒有任何按鈕的 entry === page 成立 —— 目前頁次會同時
  // 失去方括號（非色彩線索）與 aria-current，使用者與輔助技術都不知道自己在哪。
  if (current > totalPages) {
    const head: Array<number | '…'> =
      totalPages <= 2
        ? Array.from({ length: totalPages }, (_, i) => i + 1)
        : [1, '…', totalPages];
    return [...head, current];
  }
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  const out: Array<number | '…'> = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(totalPages - 1, current + 1);
  if (start > 2) out.push('…');
  for (let p = start; p <= end; p += 1) out.push(p);
  if (end < totalPages - 1) out.push('…');
  out.push(totalPages);
  return out;
}

/**
 * 使用者清單的頁碼式分頁控制（C-9 前端）。
 *
 * **必須渲染在表格／卡片容器之外**：既有的載入／錯誤態會把整個容器內容替換為
 * 單一訊息，控制項若在容器內，切頁時會連同表格一起消失、鍵盤焦點退回頁面主體。
 * 這是結構前提，不是樣式偏好。
 *
 * 邊界與單頁一律**呈現但停用**（不隱藏）：位置穩定，Tab 序不隨頁次改變，且
 * 「共 N 筆」在最常見的小資料量情況下仍然看得到。
 */
export const PaginationControl: React.FC<PaginationControlProps> = ({
  page,
  pageSize,
  total,
  isBusy,
  onPageChange,
}) => {
  // 總頁數為**導出值**，不另設 prop、不另存 state —— 兩份來源會漂移。
  const totalPages = Math.max(1, Math.ceil(total / Math.max(1, pageSize)));
  const atFirst = page <= 1;
  const atLast = page >= totalPages;
  // 小螢幕 min-w-11/min-h-11 = 44px（Tailwind v4 的 --spacing: 0.25rem × 11），
  // 桌面回到既有小按鈕的密度。
  const buttonBase =
    'min-w-11 min-h-11 md:min-w-0 md:min-h-0 px-2 py-1 text-[10px] font-bold rounded-lg ' +
    'bg-slate-800 border border-slate-700 text-slate-300 disabled:opacity-50 ' +
    'focus:outline-none focus:ring-2 focus:ring-blue-400';

  return (
    <nav
      aria-label="使用者清單分頁"
      aria-busy={isBusy}
      className="flex items-center flex-wrap gap-2 px-6 py-4"
    >
      <button
        type="button"
        disabled={atFirst || isBusy}
        onClick={() => onPageChange(page - 1)}
        className={buttonBase}
      >
        <span aria-hidden="true">{'«'}</span>
        <span className="hidden md:inline ml-1">上一頁</span>
        <span className="sr-only">上一頁</span>
      </button>

      {pageSequence(page, totalPages).map((entry, index) =>
        entry === '…' ? (
          <span
            key={`gap-${index}`}
            aria-hidden="true"
            className="px-1 text-[10px] text-slate-500"
          >
            …
          </span>
        ) : (
          <button
            key={entry}
            type="button"
            disabled={isBusy || totalPages <= 1}
            aria-current={entry === page ? 'page' : undefined}
            onClick={() => onPageChange(entry)}
            className={
              entry === page
                ? `${buttonBase} bg-blue-500/20 text-blue-300 font-extrabold`
                : buttonBase
            }
          >
            {/* 方括號是**非色彩**的目前頁次線索（WCAG 1.4.1）—— 顏色只是輔助。
                逐字沿用已核可線框的 `1 [2] 3` 表達，不發明新語彙。 */}
            {entry === page ? `[${entry}]` : entry}
          </button>
        )
      )}

      <button
        type="button"
        disabled={atLast || isBusy}
        onClick={() => onPageChange(page + 1)}
        className={buttonBase}
      >
        <span className="hidden md:inline mr-1">下一頁</span>
        <span className="sr-only">下一頁</span>
        <span aria-hidden="true">{'»'}</span>
      </button>

      <span className="ml-auto text-xs text-slate-300">
        <span className="hidden md:inline">共 </span>
        {total} 筆
      </span>
    </nav>
  );
};
