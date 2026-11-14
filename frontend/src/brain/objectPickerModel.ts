/**
 * objectPickerModel.ts — `U16` 切換對象選單的純函式（`frontend-components.md` §五之二、`security-design.md` §二之一、§五）
 *
 * **契約**：本檔每個匯出都是純函式——不碰 React state、不碰 `fetch`、不碰瀏覽器儲存、沒有主控台輸出
 * （選單檔案集合的 lint 區塊承載，`eslint.config.js`）。
 *
 * - **擁有者判定只有一處**（`BR13.2`／`BR14.3`、`OPN-12`）：可選性與「+ 新增系統」都呼叫 `isOwnedByMe`。
 *   **這不是授權**——伺服器仍以 `K2` 判定與擁有者範圍解析；本函式只決定畫面是否出現必然被拒的控件。
 * - **識別碼型別在此轉換**（`OPN-21`）：HTTP 回應的 id 是數字、`set_work_target` 與 `work_target` 的 id
 *   是字串。送出值（`targetIdsFor*`）與「目前」比較的鍵（`rowKey`／`currentRowKey`）都在本檔以 `String()`
 *   產生，兩邊經過同一個轉換，杜絕一邊漏轉。
 * - **搜尋是子字串比對**（`OPN-14`）：`normalize`（NFKC＋去頭尾空白＋小寫）後以 `includes` 比對，
 *   不把使用者輸入編譯成正規表示式。
 */

import type { ProjectOut, SystemOut } from '../projects/projectsApi';
import type { WorkTargetPayload } from './brainProtocol';
import type { WorkTargetIds } from './brainSession';

export type RowKind = 'p' | 's';

/**
 * md 以上選單的固定寬度（px）。**唯一的定義處**（`review-01` `R-05`）：`ContextBar` 以它夾住左緣，
 * `ObjectPicker` 以它產生 `--picker-width`（class `md:w-(--picker-width)`），兩邊不再各寫一份。
 * 本檔唯一的非函式匯出：常數，不帶任何副作用。
 */
export const PICKER_WIDTH_PX = 384;

/** 一個專案的系統清單在本次開啟中的畫面狀態（未出現在 Map 中＝尚未請求）。 */
export interface SystemsEntry {
  status: 'loading' | 'loaded' | 'error';
  systems: SystemOut[];
}

/** `filterGroups` 的輸出：一個要渲染的群組。 */
export interface FilteredGroup {
  project: ProjectOut;
  /** 該群組系統清單的畫面狀態；`null`＝本次開啟尚未請求。 */
  entry: SystemsEntry | null;
  /** 要顯示的系統列（已套搜尋；未載入時為空陣列）。 */
  systems: SystemOut[];
  /** 搜尋有命中此群組（專案名或任一已載入系統名）；無搜尋時恆為 true。 */
  matched: boolean;
  /** 搜尋命中的是系統名（群組應自動展開顯示命中列，`N-02` 第 3 點）。 */
  systemHit: boolean;
}

/** `BR13.2`／`BR14.3` 的唯一擁有者判定。 */
export function isOwnedByMe(project: ProjectOut, userId: number): boolean {
  return project.owner_user_id === userId;
}

/** 清單列的鍵：`p:<id>`／`s:<id>`（id 一律經 `String()`，`OPN-21`）。 */
export function rowKey(kind: RowKind, id: number): string {
  return `${kind}:${String(id)}`;
}

/**
 * 伺服器回推的作業對象對應到哪一列（`BR13.3`）：有系統標系統列；只有專案標專案列；兩者皆無不標。
 * `WorkTargetPayload` 的 id 本來就是字串。
 */
export function currentRowKey(target: WorkTargetPayload | null): string | null {
  if (!target) return null;
  if (target.systemId !== null) return `s:${target.systemId}`;
  if (target.projectId !== null) return `p:${target.projectId}`;
  return null;
}

/** 選定專案列 → `set_work_target` 的三層 id（`BR11.2`、`BR13.1`）。 */
export function targetIdsForProject(project: ProjectOut): WorkTargetIds {
  return { projectId: String(project.id), systemId: null, diagramId: null };
}

/** 選定系統列 → `set_work_target` 的三層 id；專案取系統自身的 `project_id`（`BR11.2`）。 */
export function targetIdsForSystem(system: SystemOut): WorkTargetIds {
  return { projectId: String(system.project_id), systemId: String(system.id), diagramId: null };
}

/** 搜尋與名稱的正規化：NFKC（全形→半形）、去頭尾空白、小寫。 */
export function normalize(text: string): string {
  return text.normalize('NFKC').trim().toLowerCase();
}

/**
 * 搜尋過濾（`BR13.4`，以 `N-02` 第 3 點為準）。
 *
 * - 查詢為空：全部群組照原順序（伺服器 id 遞增，前端不重排），系統列為已載入者。
 * - 專案名命中：整組保留（顯示該組全部已載入系統）。
 * - 否則只留名稱命中的已載入系統；有命中者 `systemHit`。
 * - 系統清單載入失敗的群組照列（`matched` 依專案名），讓該群組的錯誤與重試仍看得到（`F-05`）。
 * - 其餘群組不顯示。
 */
export function filterGroups(
  projects: readonly ProjectOut[],
  systemsByProject: ReadonlyMap<number, SystemsEntry>,
  query: string
): FilteredGroup[] {
  const q = normalize(query);
  const out: FilteredGroup[] = [];
  for (const project of projects) {
    const entry = systemsByProject.get(project.id) ?? null;
    const loaded = entry && entry.status === 'loaded' ? entry.systems : [];
    if (q === '') {
      out.push({ project, entry, systems: loaded, matched: true, systemHit: false });
      continue;
    }
    if (normalize(project.name).includes(q)) {
      out.push({ project, entry, systems: loaded, matched: true, systemHit: false });
      continue;
    }
    const hits = loaded.filter((s) => normalize(s.name).includes(q));
    if (hits.length > 0) {
      out.push({ project, entry, systems: hits, matched: true, systemHit: true });
      continue;
    }
    if (entry && entry.status === 'error') {
      out.push({ project, entry, systems: [], matched: false, systemHit: false });
    }
  }
  return out;
}
