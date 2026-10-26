/**
 * membershipApi.ts — `U24` 的成員域抓取函式層
 *
 * **契約（前端依賴，請勿變更）**
 *
 * 本檔的每一個函式都是**純抓取**：發請求、回傳資料或拋例外，**完全不碰 state**。
 * 這不是風格偏好——`react-hooks/set-state-in-effect` 是 **error** 級規則且會做
 * 過程間分析：只要 `useEffect` 同步呼叫的函式內部有 `setState` 就會被擋，CI 紅燈
 * （`TS-U24-4`、`team.md` 的前端 lint 結構約束）。state 更新一律留在呼叫端的
 * `.then`／`.catch`／`.finally`。
 *
 * 沿用既有形狀的三處（`team.md` Code Style，不自創抽象）：
 *   - URL 一律經 `apiUrl()`（`TS-U24-3`；既有 52 處 `fetch()` 一致沿用）
 *   - 手寫 `Authorization: Bearer`（既有 40 處同形；本 repo 未集中認證標頭）
 *   - 以 `res.ok` 判斷並取 `data.detail` 當錯誤訊息
 *
 * **型別採用產生的型別，不手寫 interface**（同 `AdminPage.tsx:8-13` 的逐字理由）：
 * 手寫的本地 interface 與後端回應形狀之間沒有任何編譯期連結，後端改欄位時
 * `tsc` 完全無感——而那正是 `openapi.json` → `api.d.ts` 這條鏈要消除的落差。
 *
 * **每一條對使用者無聲的失敗路徑都呼叫 `emitFailureSignal()`**（`SEC-U24-6`
 * 的兜底規則）。訊號的兩個欄位都是字面值聯集，故無法夾帶使用者文字（`SEC-U24-1`）。
 */

import { apiUrl } from '../config/api';
import type { components } from '../types/api';
import { emitFailureSignal } from './failureSignal';

export type MemberView = components['schemas']['MemberView'];
export type ReselectionOut = components['schemas']['ReselectionOut'];
export type LastAdminGuardReport = components['schemas']['LastAdminGuardReport'];
export type ProjectRole = components['schemas']['ProjectRole'];

/** `/api/membership` 之下的六個端點共用的前綴（`main.py` 的 mount prefix）。 */
const BASE = '/api/membership';

/**
 * per-project 角色的封閉列舉值（`ProjectRole`：`project_admin` | `member`）。
 *
 * **刻意不含 `project_owner`**：`owner` 是 `projects.owner_user_id` 承載的
 * **專案屬性**，不是成員角色（`membership_types.py` 的 `ProjectRole` docstring
 * 逐字記載，混為一談會讓「改某人的角色」意外改到專案擁有權）。
 * 邀請與改角色的下拉只提供這兩個值（`SEC-U24-4` 的前置：列舉外值會回 422）。
 */
export const PROJECT_ROLE_OPTIONS: ReadonlyArray<{ value: ProjectRole; label: string }> = [
  { value: 'member', label: '一般成員' },
  { value: 'project_admin', label: '專案管理者' },
];

/** per-project 角色的顯示名稱。未知值原樣顯示，不吞掉（伺服器是真相來源）。 */
export function projectRoleLabel(role: string): string {
  if (role === 'project_admin') return '專案管理者';
  if (role === 'member') return '一般成員';
  if (role === 'project_owner') return '專案擁有者';
  return role;
}

/**
 * 可帶守門回報的錯誤（`BR24.2`）。
 *
 * 409 的回應本體**就是** `LastAdminGuardReport`（不是 `{"detail": ...}` 的包裝）
 * ——`membership_router.py` 的 `_guard_response` 以 `JSONResponse` 直接回傳它。
 * 故這裡把 `report` 帶出來，讓呼叫端能列出**每一個**被守門的專案名稱。
 */
export class LastAdminGuardError extends Error {
  readonly report: LastAdminGuardReport;

  constructor(report: LastAdminGuardReport) {
    super('此操作會讓專案失去最後一位專案管理者');
    this.name = 'LastAdminGuardError';
    this.report = report;
  }
}

/** 權限不足（403）。呼叫端據此走**終態**處置，不重試、不重抓（見 `MembersListPage`）。 */
export class MembershipForbiddenError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MembershipForbiddenError';
  }
}

/**
 * 成員清單／成員詳情查不到專案（404）時顯示的**固定句**；邀請、移出、改角色三個寫入函式
 * 遇到 404 也丟同一個 `ProjectNotFoundError`（審查 review-02 `R-07`）。
 *
 * 與 `ProjectDetailPage` 的 `ProjectNotFound` 同語意（「不存在，或你不是它的成員」）。
 * **不顯示伺服器訊息**：合併前必修第 14 項起，後端對「不存在」與「存在但非成員」回同一個
 * 不含 id 的 404；前端改用固定句，使畫面也不依伺服器文字而變、不出現專案編號。
 */
export const PROJECT_NOT_FOUND_MESSAGE = '查不到這個專案';

/** 查不到專案（404）。呼叫端據此走**終態**處置，與 403 一樣不重試。 */
export class ProjectNotFoundError extends Error {
  constructor() {
    super(PROJECT_NOT_FOUND_MESSAGE);
    this.name = 'ProjectNotFoundError';
  }
}

/**
 * 邀請被拒（422 且 `detail` 為**字串**）＝受邀者缺全域功能權限（`AC12.5.1`）。
 *
 * 與 pydantic 的驗證錯誤（`detail` 為**物件陣列**）分流的理由見 `invite_member`。
 */
export class InviteRejectedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InviteRejectedError';
  }
}

/** 讀取回應主體；非 JSON（例如 204 或 proxy 的 HTML 錯誤頁）時回 null，不拋。 */
async function readJson(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/** 從任意回應主體取 `detail` 字串；取不到則用 fallback。**不渲染非字串 detail**。 */
function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    // 只接受字串。物件陣列是 pydantic 的 `ValidationError[]`，把它當文案會在
    // 畫面上渲染出 `[object Object]` 或 JSON 片段（`SEC-U24-4` 禁止）。
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

/** 1：成員清單（`GET /projects/{id}/members` → `List[MemberView]`）。 */
export async function fetchMembers(token: string, projectId: number): Promise<MemberView[]> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/projects/${projectId}/members`), {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    // 網路層失敗：對使用者會顯示錯誤文字，但例外本身無聲 → 仍須訊號（兜底規則）。
    emitFailureSignal({ kind: 'members-fetch-failed', endpoint: 'GET /projects/:id/members' });
    throw new Error('連線失敗');
  }
  const body = await readJson(res);
  if (!res.ok) {
    emitFailureSignal({ kind: 'members-fetch-failed', endpoint: 'GET /projects/:id/members' });
    // 合併前必修第 14 項（`[PP-MB14]`=A）起：「專案不存在」與「存在但你不是成員」
    // 後端一律回同一個 404 → 顯示固定句（不顯示伺服器訊息、不含專案編號）。
    if (res.status === 404) {
      throw new ProjectNotFoundError();
    }
    // 403 於此端點只剩「缺全域 `K3.view`」一種（非成員已改回 404）。
    if (res.status === 403) {
      throw new MembershipForbiddenError(detailMessage(body, '你沒有檢視這個專案成員的權限'));
    }
    throw new Error(detailMessage(body, '讀取成員失敗'));
  }
  return (body ?? []) as MemberView[];
}

/**
 * 2：邀請（`POST /projects/{id}/members` → **201** `MemberView`）。
 *
 * **非冪等，呼叫端不得自動重試**（後端 `BR3.3` 逐字）。
 *
 * **422 有兩種語意，以 `detail` 的型別分流**（`BR23.1`／`SEC-U24-4`）：
 *   - `detail` 為**字串** → 受邀者缺全域功能權限 → `InviteRejectedError`，
 *     對話框**停在開啟態**並顯示該字串，清單不新增任何列（`AC12.5.3`）。
 *   - `detail` **不是**字串（pydantic 的 `ValidationError[]`，例如角色不在封閉
 *     列舉內）→ 走一般錯誤路徑，**不把陣列當文案顯示**。經設計的 UI 下可達性
 *     低（角色是封閉列舉的 select），但不是零：請求可被改寫、列舉值可能漂移。
 */
export async function inviteMember(
  token: string,
  projectId: number,
  userId: number,
  role: ProjectRole
): Promise<MemberView> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/projects/${projectId}/members`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ user_id: userId, role }),
    });
  } catch {
    emitFailureSignal({ kind: 'invite-validation-failed', endpoint: 'POST /projects/:id/members' });
    throw new Error('連線失敗');
  }
  const body = await readJson(res);
  if (!res.ok) {
    if (res.status === 422) {
      const detail =
        body && typeof body === 'object' && 'detail' in body
          ? (body as { detail: unknown }).detail
          : undefined;
      if (typeof detail === 'string') {
        // 拒絕態是**設計上的結果**而非故障，但它對使用者有文字說明，不屬無聲路徑。
        throw new InviteRejectedError(detail);
      }
      // 驗證錯誤分支：使用者看到的是一句通用文案（不含陣列內容），故此路徑的
      // 真實原因對使用者是無聲的 → 必須有訊號（`SEC-U24-6` 第三條）。
      emitFailureSignal({
        kind: 'invite-validation-failed',
        endpoint: 'POST /projects/:id/members',
      });
      throw new Error('邀請的內容不符合格式要求，請重新選擇');
    }
    emitFailureSignal({ kind: 'write-forbidden', endpoint: 'POST /projects/:id/members' });
    // 寫入途中被移出或專案被刪 → 與清單同一個固定句（審查 review-02 `R-07`）。
    if (res.status === 404) {
      throw new ProjectNotFoundError();
    }
    if (res.status === 403) {
      throw new MembershipForbiddenError(detailMessage(body, '你沒有管理這個專案的權限'));
    }
    throw new Error(detailMessage(body, '邀請成員失敗'));
  }
  return body as MemberView;
}

/**
 * 3：移出（`DELETE /projects/{id}/members/{uid}` → **204**；**409** 為守門）。
 *
 * 後端對已非成員回 204（冪等）。409 帶 `LastAdminGuardReport` 本體。
 */
export async function removeMember(
  token: string,
  projectId: number,
  userId: number
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/projects/${projectId}/members/${userId}`), {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    emitFailureSignal({
      kind: 'write-forbidden',
      endpoint: 'DELETE /projects/:id/members/:uid',
    });
    throw new Error('連線失敗');
  }
  if (res.status === 204) return;
  const body = await readJson(res);
  if (res.status === 409) {
    throw new LastAdminGuardError((body ?? { projects: [] }) as LastAdminGuardReport);
  }
  emitFailureSignal({ kind: 'write-forbidden', endpoint: 'DELETE /projects/:id/members/:uid' });
  // 已非成員的目標回 204（冪等），故 404 只剩「專案不存在或呼叫者不是成員」→ 固定句。
  if (res.status === 404) {
    throw new ProjectNotFoundError();
  }
  if (res.status === 403) {
    throw new MembershipForbiddenError(detailMessage(body, '你沒有管理這個專案的權限'));
  }
  throw new Error(detailMessage(body, '移出成員失敗'));
}

/**
 * 4：改角色（`PATCH /projects/{id}/members/{uid}` → `MemberView`；**409** 為守門）。
 *
 * 一個專案可同時有**多位** `project_admin`；指定第二位不覆寫第一位（後端 `BR3.5`）。
 */
export async function changeMemberRole(
  token: string,
  projectId: number,
  userId: number,
  role: ProjectRole
): Promise<MemberView> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/projects/${projectId}/members/${userId}`), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ role }),
    });
  } catch {
    emitFailureSignal({ kind: 'write-forbidden', endpoint: 'PATCH /projects/:id/members/:uid' });
    throw new Error('連線失敗');
  }
  const body = await readJson(res);
  if (!res.ok) {
    if (res.status === 409) {
      throw new LastAdminGuardError((body ?? { projects: [] }) as LastAdminGuardReport);
    }
    emitFailureSignal({ kind: 'write-forbidden', endpoint: 'PATCH /projects/:id/members/:uid' });
    if (res.status === 404) {
      throw new ProjectNotFoundError();
    }
    if (res.status === 403) {
      throw new MembershipForbiddenError(detailMessage(body, '你沒有管理這個專案的權限'));
    }
    throw new Error(detailMessage(body, '變更角色失敗'));
  }
  return body as MemberView;
}

/**
 * 5：待確認的自動改選事件（`GET /reselections/pending` → `List[ReselectionOut]`）。
 *
 * **403 於此端點代表缺 `K3 view`，屬永久失敗**（`BR21.3`）。但正常情況下
 * 呼叫端**根本不會走到這裡**——`can("K3","view")` 是發出請求的**前置條件**
 * （`security-design.md` §一之二），故缺該權限者的請求數是 **0** 而不是「失敗 1 次」。
 * 本函式的 403 分支處理的是「發出後才發現」的殘餘情形（權限剛被改）。
 *
 * **整條路徑對使用者完全無聲**（`BR21.3`：宿主保持空、不顯示錯誤），
 * 故每一種非 2xx 與網路失敗都必須有訊號——不只 403（`SEC-U24-6` 第二條逐字）。
 */
export async function fetchPendingReselections(token: string): Promise<ReselectionOut[]> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/reselections/pending`), {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    emitFailureSignal({ kind: 'banner-fetch-failed', endpoint: 'GET /reselections/pending' });
    throw new Error('banner_fetch_failed');
  }
  if (!res.ok) {
    emitFailureSignal({
      // 403 與其他失敗分開：前者是永久失敗（本工作階段不再發請求），
      // 後者下次落地可重試。兩者都無聲，但處置不同。
      kind: res.status === 403 ? 'banner-forbidden' : 'banner-fetch-failed',
      endpoint: 'GET /reselections/pending',
    });
    // 以 `name` 區分永久／暫時，而不是把 HTTP 狀態碼外洩給呼叫端自己判。
    const err = new Error('banner_fetch_failed');
    err.name = res.status === 403 ? 'BannerForbidden' : 'BannerFetchFailed';
    throw err;
  }
  const body = await readJson(res);
  return (body ?? []) as ReselectionOut[];
}

/**
 * 6：標記單一事件為已讀（`POST /reselections/{eid}/acknowledge` → **204**）。
 *
 * **此端點不冪等，而 404 等價於成功**（`BR26.3`）：404 的語意逐字是
 * 「查不到該事件、它不屬於你，或**它已被確認**」。把它當失敗會讓橫幅
 * **永遠清不掉**——N 筆中第 2 筆失敗後再按一次，第 1 筆這次回 404，
 * 若視為「任一失敗」就又回到錯誤態，而伺服器上那幾筆已是已讀，
 * 本機與伺服器**永久分歧**（`AC12.5.3` 拒絕的半套狀態）。
 *
 * @returns `true` ＝該事件已確認（204 或 404），可從本機移除；`false` ＝未成功，須留下。
 */
export async function acknowledgeReselection(token: string, eventId: number): Promise<boolean> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${BASE}/reselections/${eventId}/acknowledge`), {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    emitFailureSignal({
      kind: 'banner-fetch-failed',
      endpoint: 'POST /reselections/:eid/acknowledge',
    });
    return false;
  }
  if (res.status === 204 || res.status === 404) return true;
  emitFailureSignal({
    kind: 'banner-fetch-failed',
    endpoint: 'POST /reselections/:eid/acknowledge',
  });
  return false;
}
