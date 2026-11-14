/**
 * failureSignal.ts — `U24 member-pages-ui` 的失敗訊號（`SEC-U24-6` 的承載形狀）
 *
 * **契約（請勿放寬型別）**
 *
 * 兩個欄位都是**字面值聯集**，不是開放的 `string`。這是 `SEC-U24-1`
 * （console 不得含使用者文字或識別字）唯一的型別層保證：
 *
 *   - `kind: \`invite-failed:${displayName}\`` → **編譯失敗**
 *   - `endpoint: '/api/membership/projects/7/members/42'` → **編譯失敗**
 *
 * 初版曾把兩欄寫成 `string` 並宣稱那是結構保證，`nfr-design` 的審查 `R-04`
 * 判為高估並要求改為字面值聯集——把欄位從介面移除（無 `message`／`detail`／
 * `displayName`）只是關掉最方便的那條通道，開放的 `string` 仍可塞進任何東西。
 *
 * **刻意沒有 `message`／`detail`／`displayName` 三個欄位**：本 repo 為 public、
 * GitHub Actions log 公開可讀，一次意外輸出即等同公開發布
 * （`project.md` 的機敏資料禁令、ADR-0006 的 audit logging 面）。
 *
 * **端點標識用路徑樣板而非實際值**：實際的 `project_id`／`user_id` 是識別字，
 * 落在 `SEC-U24-1` 的禁止範圍內。六個端點全部可僅以 method ＋ 路徑樣板區分。
 *
 * `SEC-U24-6` 是**兜底規則**而非三條列舉：本單元**每一條對使用者無聲的失敗
 * 路徑**都必須輸出一筆訊號。列舉型要求若沒有兜底句，沒被點名的路徑就是新的
 * 靜默面——而 `construction.md` 的 phase guardrail 逐字禁止 silent failure。
 */

/** 無聲失敗的種類。新增種類時在此擴充聯集，不得改成 `string`。 */
export type SignalKind =
  | 'members-fetch-failed'
  | 'banner-fetch-failed'
  | 'banner-forbidden'
  | 'invite-validation-failed'
  | 'write-forbidden';

/**
 * 六個端點的 method ＋ 路徑樣板。
 *
 * **樣板，不是實際路徑**：`:id`／`:uid`／`:eid` 是字面的佔位符，填入實際 id
 * 會因為不在聯集內而編譯失敗——那正是本型別存在的目的。
 */
export type SignalEndpoint =
  | 'GET /projects/:id/members'
  | 'POST /projects/:id/members'
  | 'DELETE /projects/:id/members/:uid'
  | 'PATCH /projects/:id/members/:uid'
  | 'GET /reselections/pending'
  | 'POST /reselections/:eid/acknowledge';

/** 一筆失敗訊號。**兩個欄位，沒有第三個。** */
export interface FailureSignal {
  kind: SignalKind;
  endpoint: SignalEndpoint;
}

/**
 * 輸出一筆失敗訊號。
 *
 * 以 `console.warn` 而非 `console.error`：這些路徑對使用者無聲且多為可預期的
 * 權限／網路狀況，不是程式缺陷。輸出內容限於上面兩個封閉欄位的值——
 * 訊號本身不接受任何額外參數，故呼叫端無法在此附加使用者文字。
 */
export function emitFailureSignal(signal: FailureSignal): void {
  // 單一字串而非物件：Playwright 的 `page.on('console')` 讀 `msg.text()`，
  // 物件在那裡會序列化成 `JSHandle@object` 而讓 `SEC-U24-6` 的斷言無法比對。
  console.warn(`[membership] ${signal.kind} ${signal.endpoint}`);
}
