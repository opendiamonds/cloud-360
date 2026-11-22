/**
 * objectCreateAction.ts — 建立專案與建立系統的**唯一**寫入路徑（`BR82.1`）
 *
 * **契約（`U16 object-picker-ui` 沿用，請勿另建建立路徑；`OPEN-PP23-8`）**
 *
 * - 名稱去頭尾空白後為空 → 送出前擋下（`ObjectCreateError('empty')`），**不發請求**。
 * - 失敗分三類文案（`BR82.2`）：409 → 名稱重複；403 → 無權限；其餘（含網路失敗、422）→ 其他。
 *   名稱由呼叫端的表單保留，本函式不清除任何東西。
 * - **非冪等，一次呼叫恰發一次請求，不自動重試**（`BR82.3`，後端 `BR2.4`）。pending 期間的
 *   重複觸發由呼叫端的進行中旗標擋下。
 *
 * 純函式層：不碰 React state；成功回傳伺服器建立的物件（其 `id` 決定導向目的地）。
 */

import {
  ApiError,
  createProject,
  createSystem,
  type ProjectOut,
  type SystemOut,
} from './projectsApi';

export type CreateKind = 'project' | 'system';
export type CreateErrorKind = 'empty' | 'duplicate' | 'forbidden' | 'other';

const MESSAGES: Record<CreateKind, Record<CreateErrorKind, string>> = {
  project: {
    empty: '請輸入名稱',
    duplicate: '已有同名的專案，請換一個名稱',
    forbidden: '你沒有建立專案的權限，請聯絡管理者',
    other: '建立專案失敗，請稍後再試',
  },
  system: {
    empty: '請輸入名稱',
    duplicate: '這個專案已有同名的系統，請換一個名稱',
    forbidden: '你沒有在這個專案建立系統的權限',
    other: '建立系統失敗，請稍後再試',
  },
};

export class ObjectCreateError extends Error {
  readonly kind: CreateErrorKind;

  constructor(objectKind: CreateKind, kind: CreateErrorKind) {
    super(MESSAGES[objectKind][kind]);
    this.name = 'ObjectCreateError';
    this.kind = kind;
  }
}

function classify(err: unknown): CreateErrorKind {
  if (err instanceof ApiError) {
    if (err.status === 409) return 'duplicate';
    if (err.status === 403) return 'forbidden';
  }
  return 'other';
}

export async function objectCreateAction(
  token: string,
  kind: 'project',
  name: string
): Promise<ProjectOut>;
export async function objectCreateAction(
  token: string,
  kind: 'system',
  name: string,
  parentProjectId: number
): Promise<SystemOut>;
export async function objectCreateAction(
  token: string,
  kind: CreateKind,
  name: string,
  parentProjectId?: number
): Promise<ProjectOut | SystemOut> {
  const trimmed = name.trim();
  if (!trimmed) throw new ObjectCreateError(kind, 'empty');
  try {
    if (kind === 'project') return await createProject(token, trimmed);
    if (parentProjectId === undefined) throw new ObjectCreateError(kind, 'other');
    return await createSystem(token, parentProjectId, trimmed);
  } catch (err) {
    if (err instanceof ObjectCreateError) throw err;
    throw new ObjectCreateError(kind, classify(err));
  }
}
