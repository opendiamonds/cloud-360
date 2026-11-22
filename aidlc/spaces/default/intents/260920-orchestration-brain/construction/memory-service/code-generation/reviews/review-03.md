## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25T13:12:00Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/user_router.py:510-517（`_blocking_user_references` 的 `memory_records`／`memory_audit_events` 兩列） | `hierarchy-data` 以 ORM 直接對 `MemoryRecord`、`MemoryAuditEvent` 做 `.count()`，繞過 `MemoryFacade`。實際影響有限：只讀、只算筆數、條件固定為「該 uid 自己的列」、用於刪除帳號前的外鍵預檢（facade 的 `Principal` 授權與 `MemoryView` 不適用此情境），沒有洩漏內容，也沒有寫入，不構成 ADR-0006 IAM 或 audit 缺口。但目前沒有任何測試或文件宣告這是「facade 唯一入口」的合法例外；`test_memory_contract.py` 只鎖 router 不得 import service，沒鎖「其他模組不得讀記憶表」。日後有人照樣在別處直接查記憶表時，這條規則就失去判準。另一個連帶後果：只要某使用者刪過任何一筆記憶，`memory_audit_events.actor_user_id`（NOT NULL FK、稽核不刪）就會讓該帳號之後永遠被擋成 409，這是 OQ-H1 規則 2 已裁決的結果，但本單元的契約沒有記載它。 | 在 `memory_facade.py` 或 `unit-test-instructions.md` 記一句：`user_router._blocking_user_references` 是 facade 唯一入口的已知例外（唯讀計數、僅本人 uid、用於刪除預檢）；並補一條靜態斷言，列舉允許直接 import 記憶 ORM 模型的模組（`memory_*`、`user_router`），讓新增者必須有意識地改清單。 | Unresolved |
| R-02 | Minor | backend/services/memory_errors.py:`class MemoryError(Exception)`；memory_facade.py:88、:502（匯入並放進 `__all__`） | 領域例外基底類別與 Python 內建 `MemoryError`（記憶體耗盡）同名。`memory_facade.py` 以同名匯入並重新匯出，任何 `from services.memory_facade import *` 或 `U11` 寫 `except MemoryError` 的人會悄悄遮蔽內建例外，或反過來抓不到真正的 OOM。目前 repo 內沒有其他模組匯入它，所以尚未造成錯誤，但 `intent-router` 修合併前必修第 13 項時正要在 `intent_routing.py` 分辨這些例外型別，是最可能踩到的人。 | 改名為不衝突的名稱（例如 `MemoryServiceError`），或保留舊名並在檔頭與 `__all__` 旁明寫「不得與內建同名使用」。屬契約型別變更，需同步通知 `intent-router`、`memory-page-ui`，故列 Minor 而非本輪必修。 | Unresolved |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/code-generation/code-summary.md §三 查驗表 Step 1.3、1.4、8.3（及 2.4、5.5、10.3 三格未勾的處理） | 重點 (c) 的判斷：三格維持未勾是誠實的，因為字面要求確實與實作不符，且偏離理由已逐格記載。但有兩個不對稱。其一，Step 1.3、1.4、8.3 的字面判準是「開工前時點檢查」或「無 git 基準可比」，本輪也標「成立（以現況判）」，改用替代判準勾選；這與 2.4、5.5、10.3 不勾的標準不一致（同樣是字面無法成立，卻一個勾一個不勾）。其二，2.4、5.5、10.3 三格都已有刻意偏離理由，卻仍以未勾懸在計畫上，閘門讀者無法一眼看出它們是「已接受偏離」還是「未完成」。 | 兩選一：(a) 把 1.3、1.4、8.3 也改為「維持未勾，替代判準成立」，與其餘三格同標準；(b) 在計畫對應步驟上就地加註「接受偏離，見 code-summary §三」並勾選。不需要改程式。 | Unresolved |
| R-04 | Major | backend/services/memory_service.py:`scored_candidates`（取負號）、`search_records`、`create_record` 的 `UPDATE ... CAST(:embedding AS vector)`；backend/tests/test_memory_ranking.py:90（只在註解提到 `scored_candidates`） | 檢索與向量寫入這兩條核心路徑在 repo 的自動化測試裡完全沒有被執行。我 grep `tests/*.py`，`scored_candidates`、`_vector_literal`、`_supports_vector`、`SET embedding` 零個實際呼叫；`search_records` 只在 `test_memory_pending_authz` 被 mock 成回空。`scored_candidates` 的 docstring 宣稱「`rank_candidates` 的 PBT 第 2 條性質是它唯一的機械防線」，但該 PBT 餵的是任意手造分數，驗不到「距離要取負號」。把 `score=-distance` 改成 `score=distance`，ranking 會整個反過來（最不相似排最前），所有 50 個測試仍然全綠。同樣，`create_record` 在 SQLite 上跳過 `UPDATE`，PostgreSQL 上的寫入向量沒有任何測試；一旦失效，每列 `embedding` 都是 NULL，檢索永遠回空而不報錯。`verify_memory_schema.sql` 的 S15 是另一份查詢的複本，且它直接 INSERT 向量，沒有走 `create_record`，所以也驗不到這兩處。這是本單元宣稱的「唯一完全靜默的失敗模式」，卻沒有可以變紅的測試。 | 補測試讓兩處可失敗：(1) 對 `scored_candidates` 寫純單元測試，斷言距離較小者分數較大，且經 `rank_candidates` 後最近的排第一；(2) 對 `search_records`／`create_record` 加一組以 mock 或 `str(compiled)` 驗證的測試（斷言 `_supports_vector` 為真時確實送出 `UPDATE ... SET embedding`、`kinds` 與向量字面值綁定正確），或把「寫入後檢索得到」納入 `verify_memory_schema.sql` 並說明在 CI 的位置。完成後做一次突變（取負號改回、略過 UPDATE）確認紅燈。 | New |
| R-05 | Minor | backend/services/memory_service.py:`delete_with_audit`；backend/services/memory_facade.py:`delete` | 開發者的觀察「同筆記憶併發刪除可能 500」方向不對。我用兩個 session 各自取到同一列後依序呼叫 `delete_with_audit`，實測第二次不報錯（只有 SAWarning「expected to delete 1 row(s); 0 were matched」），並且**多寫了第二筆 `deleted_by_user` 稽核**（稽核列數 2）。這違反 `BR4.3` 與 `NFR4.21` 想避免的稽核失真（`AC4.3.2`），且在 PostgreSQL 上同樣不會擋。窗口小，但屬於稽核正確性。 | 刪除時以 `DELETE ... WHERE id = :id` 檢查 `rowcount`，為 0 就回滾並丟 `MemoryNotFound`；或在稽核寫入前先 `SELECT ... FOR UPDATE`。加一個雙 session 的回歸測試。 | New |
| R-06 | Minor | backend/services/memory_service.py:`list_records`、`SEARCH_SQL`；`functional-spec.md` 步 8 | 讀取不過濾 `expires_at`（開發者觀察屬實）。`functional-spec.md` 沒要求過濾，故不違規；但清除機制 `U9` 在 `infrastructure-design` 仍有未結項，已過 90 天的 episodic 記憶在清除前仍會被 `search` 餵進 `U11`。 | 在 `memory_service.py` 或 `code-summary.md` 明確記錄「讀取不過濾過期列，依賴 U9 清除」為已接受取捨，並指派承接站；或加 `expires_at IS NULL OR expires_at > now()` 條件並同步 S15。 | New |
| R-07 | Minor | backend/services/memory_service.py:`log_denied`；backend/services/memory_facade.py:`_authorize_approved`、`delete` | 拒絕日誌以 `%s` 原樣寫入呼叫端提供的 `memory_id`。`DELETE /records/{memory_id}` 的路徑參數是任意字串（百分比編碼的換行會被解碼），可偽造日誌行或灌入超長字串。沒有內容外洩，但 `NFR7.30` 的日誌是「有人在枚舉」的唯一偵測手段，被汙染會降低其可信度。 | 記錄前截斷長度並以 `%r` 或去除控制字元的方式輸出；補一條含換行 id 的斷言。 | New |
| R-08 | Minor | backend/services/memory_router.py:`MemoryCreateRequest.content`；memory_facade.py:`write`、`search` | `content` 與檢索 `query` 沒有任何長度上限，會直接送進 embedding 提供者並寫入 `TEXT`。已認證使用者可用超大酬載消耗 embedding 資源與儲存；`NFR7.28`／`NFR7.29` 只限列出與 `limit`。 | 在 router 加 `max_length`（並同步 `openapi.json`），或在 facade 以 `MemoryInvalidInput` 拒絕，並記錄上限值的來源。 | New |

> R-01 Reviewer note: `user_router.py:510-517` 仍直接以 ORM 計數 `MemoryRecord`／`MemoryAuditEvent`；`memory_facade.py` 檔頭「殘留缺口」與 `unit-test-instructions.md` 皆未宣告此例外，`test_memory_contract` 也沒有限制「哪些模組可 import 記憶 ORM」的斷言。`code-summary.md` 重做節只在散文裡提到，不是契約或測試。

> R-02 Reviewer note: `memory_errors.py` 的基底類別仍叫 `MemoryError`，`memory_facade.py` 仍同名匯入並放進 `__all__`。`intent_routing.py:232` 目前只捕捉 `MemoryForbidden`，尚未踩到，但風險未消除。

> R-03 Reviewer note: 計畫 2.4、5.5、10.3 三格仍未勾，計畫檔內沒有「接受偏離」的就地標註；1.3、1.4、8.3 以替代判準勾選，兩者標準仍不一致。理由只存在於 code-summary 重做節，從計畫檔讀不出來。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest`：test_memory_contract／ranking／authz／pending_authz | 50 tests OK | 測試皆綠，但如 Major 所述，檢索取負號與向量寫入路徑不在任何測試的觸及範圍內。 |
| 雙 session 重複刪除模擬（SQLite，拋棄式） | 第二次呼叫成功、稽核列數 2 | 證實併發刪除的後果是重複稽核而非 500。 |
| 授權檢視（facade／router／service） | 六個公開方法首行皆為 `_authorize_approved`；router 無角色字串；刪除路徑「非擁有者」與「不存在」同為 `MemoryNotFound`；放寬與稽核先判角色再取列；日誌只含 principal／memory_id／reason，未含 content | `[D1]`=A、角色先於取列、日誌不含內容等重點授權設計成立。 |

### Summary

授權設計（facade 單一入口、`[D1]`=A 統一 404、角色先於取列、日誌不含內容）與 `rank_candidates` 的排列不變性 PBT 都站得住腳，ADR-0006 的 IAM 與 audit 面向沒有發現缺口。阻擋點是：相似度檢索的取負號與 PostgreSQL 向量寫入兩條核心路徑沒有任何能變紅的測試，一旦壞掉會靜默回傳反向或空結果。另有重複稽核、日誌注入、輸入無上限等 Minor，三個前輪 Minor 仍在。
