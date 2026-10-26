/**
 * objectPickerData.ts — `U16` 切換對象選單的純抓取層（`team.md` Code Style「資料抓取拆兩層」第①層）
 *
 * **契約**：只發請求、回傳資料或拋例外（`ApiError`，帶 HTTP 狀態碼），**不碰 React state**；state 一律在
 * 呼叫端（`ObjectPicker.tsx`）的 `.then`／`.catch` 更新。本檔沒有主控台輸出（`OPN-15`）。
 *
 * 取代 `frontend-components.md` §五之一原規劃的 `fetchPickerGroups`（一次抓全部、扇出）：依
 * `functional-spec-corrections.md` `F-05` 與 `nfr-requirements-corrections.md` `N-02`，開啟時只抓專案清單，
 * 某專案的系統清單在展開該群組、或搜尋第一次非空輸入的補抓時才抓——故拆成兩個單一抓取函式。
 *
 * 不新增 `fetch` 呼叫點：兩者都經 `U23` 的 `projectsApi`（URL 經 `apiUrl()`、標頭由既有 `requestJson` 組）。
 */

import { listProjects, listSystems, type ProjectOut, type SystemOut } from '../projects/projectsApi';

/** 可見的專案（伺服器依 id 遞增；前端不重排，`BR12.1`）。 */
export function fetchProjects(token: string): Promise<ProjectOut[]> {
  return listProjects(token);
}

/** 某專案的系統清單（404＝不存在或不可見，由呼叫端呈現為該群組的錯誤，不當成「尚無系統」）。 */
export function fetchSystems(token: string, projectId: number): Promise<SystemOut[]> {
  return listSystems(token, projectId);
}
