/**
 * memoryEntry.ts — 記憶入口的**唯一**顯示判定（INV-3，`BR31.2`）
 *
 * **契約（`U14 entry-page-ui` 依賴，請勿變更）**
 *
 * 記憶有兩個入口：Sidebar 的「我的記憶」（本單元）與入口頁捷徑（`U14`，尚未施工）。
 * 兩者**一律呼叫本函式**，不得各自判斷——兩處各自判斷時，下一個加權限的人只會改
 * 一處，另一處靜默失去把關（`interaction-spec.md:33` 的 INV-3）。
 *
 * 判定內容為「已登入」：`/memory` 走 `ProtectedRoute` 不包 `CapabilityRoute`
 * （`BR31.1`），把關的是伺服器端的擁有者欄位與帳號核准狀態，不是 story id。
 * **這不是授權**：入口出現與否不影響任何人能否呼叫記憶 API。
 */

export interface MemoryEntryAuth {
  isAuthenticated: boolean;
}

export function canSeeMemoryEntry(auth: MemoryEntryAuth): boolean {
  return auth.isAuthenticated;
}
