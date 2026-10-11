import React from 'react';

/**
 * EpisodicPager — 情節記憶的「上一頁／下一頁」＋「第 N–M 則」（`BR33.2`）
 *
 * **不顯示總數、不沿用 `PaginationControl`**：該元件的 props 要求 `total`，而
 * `GET /api/memory/records` 沒有任何總筆數（`OPEN-MP15-2`）。餵近似值會顯示一個
 * 隨翻頁變大的錯數字。
 *
 * 純 props 驅動、不自行抓取。
 */
export interface EpisodicPagerProps {
  page: number;
  rangeStart: number;
  rangeEnd: number;
  hasNext: boolean;
  isBusy: boolean;
  onPageChange: (targetPage: number) => void;
}

export const EpisodicPager: React.FC<EpisodicPagerProps> = ({
  page,
  rangeStart,
  rangeEnd,
  hasNext,
  isBusy,
  onPageChange,
}) => (
  <div
    data-testid="memory-pagination"
    aria-busy={isBusy}
    className="mt-3 flex items-center justify-end gap-3 text-sm"
  >
    <span data-testid="memory-pagination-range" className="text-gray-600">
      {rangeStart > 0 ? `第 ${rangeStart}–${rangeEnd} 則` : '此頁沒有記憶'}
    </span>
    <button
      type="button"
      data-testid="memory-pagination-prev"
      onClick={() => onPageChange(page - 1)}
      disabled={page <= 1 || isBusy}
      className="rounded-md border border-gray-300 bg-white px-3 py-1 font-bold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
    >
      上一頁
    </button>
    <button
      type="button"
      data-testid="memory-pagination-next"
      onClick={() => onPageChange(page + 1)}
      disabled={!hasNext || isBusy}
      className="rounded-md border border-gray-300 bg-white px-3 py-1 font-bold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
    >
      下一頁
    </button>
  </div>
);
