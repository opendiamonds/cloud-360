/**
 * brainRoutePage.ts — 路由 → 大腦 `page` 的**唯一**對應（部署後追加「全站大腦小助手」，2026-11-15）
 *
 * 全站一條大腦連線之下，`page`（ws 契約 `UserMessagePayload.page`：entry／workspace／assessment）不再由
 * 各頁傳給自己的連線，而是由目前路由推導。對應只寫在這裡：`/workspace` → workspace、`/assessment` →
 * assessment，其餘（入口頁、專案、記憶、成本、管理頁…）→ entry，讀寫共享段——與專案頁原本以
 * `useBrainConnection('entry')` 開連線的做法一致。ws 契約與後端未改。
 *
 * 入口頁（`/`）另以 `isEntryPagePath` 判定：它本身就是整頁對話，不顯示浮動小助手。
 */

import type { BrainPage } from './brainProtocol';

const SUBPAGES: ReadonlyArray<{ prefix: string; page: Exclude<BrainPage, 'entry'> }> = [
  { prefix: '/workspace', page: 'workspace' },
  { prefix: '/assessment', page: 'assessment' },
];

function matches(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

export function pageForPath(pathname: string): BrainPage {
  return SUBPAGES.find((s) => matches(pathname, s.prefix))?.page ?? 'entry';
}

/** 入口頁的路由（`DefaultRedirect` 在具 K1 時於 `/` 渲染入口頁）。 */
export const ENTRY_PAGE_PATH = '/';

export function isEntryPagePath(pathname: string): boolean {
  return pathname === ENTRY_PAGE_PATH;
}
