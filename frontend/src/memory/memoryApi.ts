/**
 * memoryApi.ts — `U15` 記憶域的抓取函式層
 *
 * **契約（前端依賴，請勿變更）**
 *
 * 本檔的每一個函式都是**純抓取**：發請求、回傳資料或拋例外，**完全不碰 state**
 * （`react-hooks/set-state-in-effect` 為 error 級且做過程間分析，`team.md` 的前端
 * lint 結構約束）。state 更新一律留在呼叫端的 `.then`／`.catch`／`.finally`。
 *
 * 沿用 `membership/membershipApi.ts` 的形狀（`team.md` Code Style，不自創抽象）：
 *   - URL 一律經 `apiUrl()`；
 *   - 手寫 `Authorization: Bearer`；
 *   - 以 `res.ok` 判斷並取 `data.detail` 當錯誤訊息。
 *
 * **型別採用產生的型別，不手寫 interface**：手寫的本地 interface 與後端回應形狀
 * 之間沒有任何編譯期連結。
 *
 * **本檔只消費 `GET` 與 `DELETE`**（`frontend-components.md §七`）：不建立記憶、
 * 不放寬可見範圍（`BR35.3`／`SEC-U15-3`）、不查稽核。
 *
 * **記憶內容不進 console**（`SEC-U15-5`）：失敗路徑只記操作名與狀態碼。
 * **不寫任何瀏覽器儲存**（`NFR4.90`）：回傳值只交給呼叫端的 `useState`。
 */

import { apiUrl } from '../config/api';
import type { components } from '../types/api';
import type { MemoryKind } from './memoryLabels';

export type MemoryView = components['schemas']['MemoryView'];

/** `/api/memory` 之下的路由前綴（`main.py` 的 mount prefix）。 */
const BASE = '/api/memory';

/** 讀取回應主體；非 JSON（例如 204 或 proxy 的 HTML 錯誤頁）時回 null，不拋。 */
async function readJson(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/** 從回應主體取 `detail` 字串；取不到或不是字串時用 fallback。 */
function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

/**
 * 列出某一區的記憶（`GET /records?kind=&offset=&limit=` → `List[MemoryView]`）。
 *
 * `offset` 為 `undefined` 時**不帶**該參數（語意／程序區，`BR33.3`）；情節區一律
 * 顯式帶 `offset`（含第一頁的 0）。
 */
export async function fetchMemoryRecords(
  token: string,
  kind: MemoryKind,
  offset: number | undefined,
  limit: number
): Promise<MemoryView[]> {
  const params = new URLSearchParams({ kind });
  if (offset !== undefined) params.set('offset', String(offset));
  params.set('limit', String(limit));

  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/records?${params.toString()}`), {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    console.warn(`memory.list failed: network (${kind})`);
    throw new Error('連線失敗');
  }
  const body = await readJson(res);
  if (!res.ok) {
    console.warn(`memory.list failed: ${res.status} (${kind})`);
    throw new Error(detailMessage(body, '讀取記憶失敗'));
  }
  return Array.isArray(body) ? (body as MemoryView[]) : [];
}

/**
 * `deleteMemoryRecord` 的結果。
 *
 * - `'deleted'`：204，伺服器確認刪除。
 * - `'not-found-unconfirmed'`：404，**尚未確認**該則是否真的不在了。
 */
export type DeleteMemoryOutcome = 'deleted' | 'not-found-unconfirmed';

/**
 * 刪除一則記憶（`DELETE /records/{memory_id}`）。
 *
 * **404 不等於已刪除**（合併前必修第 6 項，使用者裁決「收到 404 就重新讀清單
 * 確認」）：後端對「不存在」與「不是你的」刻意回同一個 404（`[D1]`=A，防枚舉），
 * 而路徑錯誤、反向代理或部署未含該路由時回的 404 也長得一樣。前端無法以狀態碼
 * 分辨，故本函式只回具名的「待確認」結果，由呼叫端重讀清單判定（`MemoryZone`
 * 的 `deleteRecord`）。`BR34.5`（已被 90 天清除者視同刪除成功）的語意由那次重讀
 * 保留：重讀不再列出它，才視同已刪除。**不依賴錯誤訊息字串**。
 *
 * `memory_id` 是伺服器給的不透明字串，原樣放進路徑（不轉數字）。
 */
export async function deleteMemoryRecord(
  token: string,
  memoryId: string
): Promise<DeleteMemoryOutcome> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/records/${encodeURIComponent(memoryId)}`), {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    console.warn('memory.delete failed: network');
    throw new Error('連線失敗');
  }
  if (res.status === 204) return 'deleted';
  if (res.status === 404) return 'not-found-unconfirmed';
  const body = await readJson(res);
  console.warn(`memory.delete failed: ${res.status}`);
  throw new Error(detailMessage(body, '刪除失敗'));
}
