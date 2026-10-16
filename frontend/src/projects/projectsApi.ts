/**
 * projectsApi.ts — `U23` 的專案／系統／變更紀錄抓取函式層
 *
 * **契約（前端依賴，請勿變更）**
 *
 * 每一個函式都是**純抓取**：發請求、回傳資料或拋例外，**完全不碰 state**
 * （`BR88.1`；`react-hooks/set-state-in-effect` 是 error 級且做過程間分析）。
 * state 更新一律留在呼叫端的 `.then`／`.catch`／`.finally`。
 *
 * 沿用既有形狀（`team.md` Code Style，不自創抽象）：URL 一律經 `apiUrl()`、手寫
 * `Authorization: Bearer`、以 `res.ok` 判斷並取字串型 `data.detail` 當錯誤訊息。
 * 型別取自產生的 `src/types/api.d.ts`，不手寫 interface（`U24` 的先例）。
 *
 * **建立專案與建立系統的寫入點只准由 `objectCreateAction` 呼叫**（`BR82.1`）：
 * 本檔匯出 `createProject`／`createSystem`，但前端程式中它們的呼叫點恰有一處。
 *
 * 本檔沒有任何主控台輸出（`PPN-18`）；失敗一律以例外交給呼叫端，由畫面呈現。
 */

import { apiUrl } from '../config/api';
import type { components } from '../types/api';

export type ProjectOut = components['schemas']['ProjectOut'];
export type SystemOut = components['schemas']['SystemOut'];
export type DiagramChangeOut = components['schemas']['DiagramChangeOut'];

const BASE = '/api/hierarchy';

/** 帶 HTTP 狀態碼的失敗。`status` 為 0 代表網路層失敗（請求沒有回應）。 */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** 讀取回應主體；非 JSON（例如 204 或 proxy 的錯誤頁）時回 null，不拋。 */
export async function readJson(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/** 只接受字串型 `detail`；pydantic 的驗證錯誤陣列不當文案（不渲染 `[object Object]`）。 */
export function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

/** 共用的請求殼：網路失敗 → `ApiError(0)`；非 2xx → `ApiError(status, detail)`。 */
export async function requestJson(
  token: string,
  path: string,
  init: RequestInit,
  fallbackMessage: string
): Promise<unknown> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      ...init,
      headers: {
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    throw new ApiError(0, '連線失敗');
  }
  const body = await readJson(res);
  if (!res.ok) {
    throw new ApiError(res.status, detailMessage(body, fallbackMessage));
  }
  return body;
}

/** 端點 1：可見的專案（`GET /api/hierarchy/projects`，依 id 遞增）。 */
export async function listProjects(token: string): Promise<ProjectOut[]> {
  const body = await requestJson(token, `${BASE}/projects`, { method: 'GET' }, '讀取專案失敗');
  return (body ?? []) as ProjectOut[];
}

/**
 * 端點 2：某專案的系統（`GET /api/hierarchy/projects/{id}/systems`）。
 *
 * 404 代表「查不到這個專案」——不存在與不可見（非成員、被移出的建立者）是同一個回應，
 * 呼叫端據此呈現 not-found 態，**不得**呈現成「尚無系統」（`BR83.4`）。
 */
export async function listSystems(token: string, projectId: number): Promise<SystemOut[]> {
  const body = await requestJson(
    token,
    `${BASE}/projects/${projectId}/systems`,
    { method: 'GET' },
    '讀取系統清單失敗'
  );
  return (body ?? []) as SystemOut[];
}

/** 端點 3：建立專案（**非冪等**；只准由 `objectCreateAction` 呼叫）。 */
export async function createProject(token: string, name: string): Promise<ProjectOut> {
  const body = await requestJson(
    token,
    `${BASE}/projects`,
    { method: 'POST', body: JSON.stringify({ name }) },
    '建立專案失敗'
  );
  return body as ProjectOut;
}

/** 端點 4：建立系統（**非冪等**；只准由 `objectCreateAction` 呼叫）。 */
export async function createSystem(
  token: string,
  projectId: number,
  name: string
): Promise<SystemOut> {
  const body = await requestJson(
    token,
    `${BASE}/projects/${projectId}/systems`,
    { method: 'POST', body: JSON.stringify({ name }) },
    '建立系統失敗'
  );
  return body as SystemOut;
}

/**
 * 端點 7：某系統的變更紀錄（`GET /api/hierarchy/diagram-changes?system_id=`）。
 *
 * **回應不是完整變更歷史**：伺服器只回經大腦、已歸屬系統、且請求者自己擁有之圖的變更
 * （`BR86.2`；未歸屬系統的圖——`OPEN-H11`——查不到）。畫面必須照實標示。
 */
export async function listDiagramChanges(
  token: string,
  systemId: number
): Promise<DiagramChangeOut[]> {
  const body = await requestJson(
    token,
    `${BASE}/diagram-changes?system_id=${encodeURIComponent(String(systemId))}`,
    { method: 'GET' },
    '讀取變更紀錄失敗'
  );
  return (body ?? []) as DiagramChangeOut[];
}
