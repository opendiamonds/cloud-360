/**
 * memoryPaging.ts — `U15` 記憶頁的分頁與計數純函式
 *
 * **不碰 state、不碰 `fetch`、不讀 `useAuth()`**（`frontend-components.md §五之二`）。
 * 前端目前沒有 unit 測試框架（`team.md` 的 `D（不採用）`），這些函式的驗證層是
 * Playwright e2e；抽成純函式是為了日後導入 unit／property-based 測試時零重構。
 */

/** 情節記憶每頁筆數。本站取值，理由見 `functional-spec.md §四之一`（`OPEN-MP15-3`）。 */
export const EPISODIC_PAGE_SIZE = 20;

/**
 * 情節記憶的請求上限：多取一筆以探測下一頁（`BR33.1`）。
 * `21 ≤ MAX_LIST_PAGE_SIZE (200)`，故不會被伺服器的 `clamp_page_size` 收斂而
 * 使探測靜默失效。
 */
export const EPISODIC_PROBE_LIMIT = EPISODIC_PAGE_SIZE + 1;

/** 語意／程序記憶一次取得的上限＝伺服器上限（`BR33.3`）。 */
export const FULL_ZONE_LIMIT = 200;

/** 第 `page` 頁（1 起算）的 offset。 */
export function episodicOffset(page: number): number {
  return (Math.max(1, page) - 1) * EPISODIC_PAGE_SIZE;
}

export interface EpisodicPageView<T> {
  /** 實際渲染的列（至多 `EPISODIC_PAGE_SIZE` 筆；第 21 筆**不渲染**）。 */
  rendered: T[];
  hasNext: boolean;
  /** 「第 N–M 則」的 N（1 起算）。`rendered` 為空時為 0。 */
  rangeStart: number;
  /** 「第 N–M 則」的 M。`rendered` 為空時為 0。 */
  rangeEnd: number;
}

/**
 * 由一次 `limit = pageSize + 1` 的回應推導該頁畫面（`BR33.1`／`BR33.2`）。
 *
 * `items` 可能因就地刪除而少於回應當下的筆數；此時 `hasNext` 仍以**目前**陣列
 * 計算——刪除後的背景重抓（`MemoryZone`）會以伺服器的新回應覆蓋它。
 */
export function computeEpisodicPage<T>(items: readonly T[], page: number): EpisodicPageView<T> {
  const rendered = items.slice(0, EPISODIC_PAGE_SIZE);
  const offset = episodicOffset(page);
  return {
    rendered,
    hasNext: items.length > EPISODIC_PAGE_SIZE,
    rangeStart: rendered.length === 0 ? 0 : offset + 1,
    rangeEnd: rendered.length === 0 ? 0 : offset + rendered.length,
  };
}

/**
 * 背景重抓回來之後的頁次（`BR34.6`，**單一頁次調整者**）。
 *
 * 只由背景重抓的回應決定頁次：回應為空且 `page > 1` 才退**一**頁；其餘維持。
 * 就地 `filter` 之後**不**立即套用本函式——若兩處都會退頁，同一次刪除會連退兩頁
 * （nfr-design 審查 `R-03`）。
 */
export function pageAfterEmptyRefetch(fetchedCount: number, page: number): number {
  if (fetchedCount === 0 && page > 1) return page - 1;
  return page;
}

/**
 * 區標題的則數（`BR32.4`）。
 *
 * `wasFull` 為 true 時一律顯示「N+ 則」：
 *   - 語意／程序區：**首次回應**是否滿載（＝`FULL_ZONE_LIMIT`）。滿載過的區刪除
 *     一則後 `n` 變成 199，但伺服器端可能還有第 201 筆——「199 則」是一個錯的
 *     精確數（nfr-design 審查 `R-06`）。故「滿載過」是黏著的。
 *   - 情節區：是否還有下一頁。
 */
export function zoneCountLabel(n: number, wasFull: boolean): string {
  return wasFull ? `${n}+ 則` : `${n} 則`;
}
