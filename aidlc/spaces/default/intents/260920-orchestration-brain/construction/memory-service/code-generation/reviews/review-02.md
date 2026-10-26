## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-22T23:47:21Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/user_router.py:510-517（`_blocking_user_references` 的 `memory_records`／`memory_audit_events` 兩列） | `hierarchy-data` 以 ORM 直接對 `MemoryRecord`、`MemoryAuditEvent` 做 `.count()`，繞過 `MemoryFacade`。實際影響有限：只讀、只算筆數、條件固定為「該 uid 自己的列」、用於刪除帳號前的外鍵預檢（facade 的 `Principal` 授權與 `MemoryView` 不適用此情境），沒有洩漏內容，也沒有寫入，不構成 ADR-0006 IAM 或 audit 缺口。但目前沒有任何測試或文件宣告這是「facade 唯一入口」的合法例外；`test_memory_contract.py` 只鎖 router 不得 import service，沒鎖「其他模組不得讀記憶表」。日後有人照樣在別處直接查記憶表時，這條規則就失去判準。另一個連帶後果：只要某使用者刪過任何一筆記憶，`memory_audit_events.actor_user_id`（NOT NULL FK、稽核不刪）就會讓該帳號之後永遠被擋成 409，這是 OQ-H1 規則 2 已裁決的結果，但本單元的契約沒有記載它。 | 在 `memory_facade.py` 或 `unit-test-instructions.md` 記一句：`user_router._blocking_user_references` 是 facade 唯一入口的已知例外（唯讀計數、僅本人 uid、用於刪除預檢）；並補一條靜態斷言，列舉允許直接 import 記憶 ORM 模型的模組（`memory_*`、`user_router`），讓新增者必須有意識地改清單。 | New |
| R-02 | Minor | backend/services/memory_errors.py:`class MemoryError(Exception)`；memory_facade.py:88、:502（匯入並放進 `__all__`） | 領域例外基底類別與 Python 內建 `MemoryError`（記憶體耗盡）同名。`memory_facade.py` 以同名匯入並重新匯出，任何 `from services.memory_facade import *` 或 `U11` 寫 `except MemoryError` 的人會悄悄遮蔽內建例外，或反過來抓不到真正的 OOM。目前 repo 內沒有其他模組匯入它，所以尚未造成錯誤，但 `intent-router` 修合併前必修第 13 項時正要在 `intent_routing.py` 分辨這些例外型別，是最可能踩到的人。 | 改名為不衝突的名稱（例如 `MemoryServiceError`），或保留舊名並在檔頭與 `__all__` 旁明寫「不得與內建同名使用」。屬契約型別變更，需同步通知 `intent-router`、`memory-page-ui`，故列 Minor 而非本輪必修。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/code-generation/code-summary.md §三 查驗表 Step 1.3、1.4、8.3（及 2.4、5.5、10.3 三格未勾的處理） | 重點 (c) 的判斷：三格維持未勾是誠實的，因為字面要求確實與實作不符，且偏離理由已逐格記載。但有兩個不對稱。其一，Step 1.3、1.4、8.3 的字面判準是「開工前時點檢查」或「無 git 基準可比」，本輪也標「成立（以現況判）」，改用替代判準勾選；這與 2.4、5.5、10.3 不勾的標準不一致（同樣是字面無法成立，卻一個勾一個不勾）。其二，2.4、5.5、10.3 三格都已有刻意偏離理由，卻仍以未勾懸在計畫上，閘門讀者無法一眼看出它們是「已接受偏離」還是「未完成」。 | 兩選一：(a) 把 1.3、1.4、8.3 也改為「維持未勾，替代判準成立」，與其餘三格同標準；(b) 在計畫對應步驟上就地加註「接受偏離，見 code-summary §三」並勾選。不需要改程式。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 依派工限制未執行任何測試、lint、build、dump 或 Python 指令 | 不適用 | 只做讀檔與 grep。`Ran 1241 tests … OK`、兩支 validator 通過等結果來自實作方的 code-summary，本審查未獨立複驗，只核對了程式碼位置與行為是否與其敘述一致。 |
| 位置抽查（5.1、5.3、5.5、5.7 等 41 格中的 10 格） | 一致 | `memory_facade.py:184` 為 `_authorize_approved`、`:401`／`:410` 兩處皆拋 `MemoryNotFound`、`:404` 以 `REASON_OWNER` 記日誌；`memory_router.py` 恰五個路由（`:164`、`:201`、`:246`、`:280`、`:311`）；`_authorize_role` 僅一份。 |

### Summary

本單元可實作且未被後續改動破壞。(a) 計畫第十節成立：`MemoryForbidden`、`MemoryNotFound`、`MemoryInvalidInput` 與 U6 的 `EmbeddingProviderUnavailable` 彼此是不同型別、都不是 `HTTPException`，`intent-router` 現行的 `except Exception`（`intent_routing.py` 的 `_memory_notes`）才是第 13 項的病灶，修在該單元即可；「不存在」與「非擁有者」回同一個 404 已由 `[D1]`=A 定案，並以 `_authorize_approved` 先判身分的設計確保 pending 帳號的 403 不重開枚舉管道。(d) U15 加入的 `_authorize_approved` 位於 facade 層，不影響本單元判準。(e) ADR-0006 四面向無缺口。剩下三項皆為 Minor：`hierarchy-data` 的唯讀計數是未登記的 facade 例外、領域例外基底類別與內建 `MemoryError` 同名、以及未勾與勾選標準不一致。
