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
 * 刪除一則記憶（`DELETE /records/{memory_id}`）。
 *
 * 404 映射為**具名結果** `'already-gone'` 而非例外（`BR34.5`）：該則已被 90 天清除
 * 或他處刪除，對使用者而言與刪除成功相同。把它放在型別上，而不是藏在 `catch`
 * 裡的狀態碼比較。
 *
 * `memory_id` 是伺服器給的不透明字串，原樣放進路徑（不轉數字）。
 */
export async function deleteMemoryRecord(
  token: string,
  memoryId: string
): Promise<'deleted' | 'already-gone'> {
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
  if (res.status === 404) return 'already-gone';
  const body = await readJson(res);
  console.warn(`memory.delete failed: ${res.status}`);
  throw new Error(detailMessage(body, '刪除失敗'));
}
