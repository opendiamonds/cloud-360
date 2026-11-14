## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-01 | Fixed | Minor | user_router.py:475 現在經 MemoryFacade(db).count_references_to_user 取記憶筆數，檔內不再 import MemoryRecord 與 MemoryAuditEvent（grep 僅見 memory_facade 匯入，:52）。backend/tests/test_memory_reference_counts.py 以靜態斷言鎖住 import，並測預檢行為與 409 內筆數，附突變 M1a 至 M3。 |
| R-02 | Fixed | Minor | memory_errors.py:51 基底類別已更名為 MemoryServiceError，檔內註解說明遮蔽內建 MemoryError 的原因；memory_facade.py:93 與 :569 同步。test_memory_reference_counts.py 以突變 M3（補回別名）鎖住。 |
| R-06 | Fixed | Minor | SEARCH_SQL:97 已加 expires_at IS NULL OR expires_at > now()，list_records 經 _not_expired（:275-283），widen_scope 以 is_expired 視過期列為不存在；刪除刻意不過濾。讀碼判定成立；tests_pg V2 與 S15 的真實 PostgreSQL 執行仍待 CI。 |
| R-07 | Fixed | Minor | log_denied 現經 loggable_memory_id（memory_service.py:704-717、:695）只記 parse_memory_id 解析成功的整數，含換行的原字串記為固定標記 UNPARSEABLE_MEMORY_ID。test_memory_row33_remaining.py:164-170 以偽造行案例覆蓋。殘留見 New Findings 第 1 列。 |
| R-08 | Fixed | Minor | memory_router.py:182 MEMORY_CONTENT_MAX_CHARS=4000 並以 max_length 套用在 content（:208），test_memory_input_limits.py 測 4000 與 4001 邊界，含多位元組。query 端由 MEMORY_QUERY_MAX_CHARS 在 facade 截斷，test_memory_query_truncation.py 覆蓋。 |
| R-09 | Fixed | Minor | test_memory_row33_remaining.py:212 的 test_race_rethrow_uses_caller_value_and_writes_no_owner_log_or_audit 以 patch delete_with_audit 拋 MemoryNotFound，斷言以呼叫端原值（含前置零）重拋、無 reason=owner WARNING、無稽核列；檔頭記有突變 M5。 |
| R-13 | Fixed | Minor | merge-blockers.md 第 52 列已併入（本列即為併入），第 33 列亦登錄 R-01、R-02、R-06 至 R-09，並引用第 17 列。殘留的狀態欄過期見 New Findings 第 3 列。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | backend/services/memory_service.py:704-717（loggable_memory_id）；parse_memory_id:163-177 | parse_memory_id 對整數位數沒有上限，由 int() 的 4300 位數限制兜底：4300 位以內的純數字 id 仍會原樣寫入拒絕日誌（約 4300 字元一行），不再能偽造行，但仍可灌長行。merge-blockers 第 52 列已把它登錄為新 Minor，本次現況仍成立，屬已知殘留。 | 記錄前在 loggable_memory_id 對解析出的數字位數設上限（超過記固定標記），並補一條超長數字 id 的斷言；或在 code-summary 明記接受此殘留並指定承接者。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/code-generation/code-generation-plan.md:128、:213、:214（1.1、10.1、10.2 未勾）；code-summary.md「整站重跑後的勾選回復」節 | 三格未勾的理由已不成立：git diff HEAD --stat 對 backend/database.py 與 backend/requirements.txt 現在皆為空（git status 乾淨，兩檔的未提交改動已隨 ff537a7 提交），requirements.txt 內 pgvector 命中 0，NFR8.20 字面判準與實質皆成立。新節卻寫成「未勾格沿用 HEAD 的未勾理由」，與現況不符。15.2 的理由（tests_pg 未在現行位元組上於本機執行）仍成立，應維持未勾；CI run 42454550208 顯示 tests_pg 僅 C3 失敗，C3 屬 membership-service。 | 關卡核可後把 1.1、10.1、10.2 勾上並記下實測輸出；code-summary 新節改為只保留 15.2 為未勾，並更正「沿用 HEAD 理由」的敘述。15.2 待 CI 或本機一次性 PostgreSQL 實跑全綠後再勾。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md 第 33 列狀態欄；memory-service/code-generation/traceability.json MB-48 | 第 33 列狀態仍為「待修（2026-10-30 登錄）」，但 (a)(b)(c)(d)(e)(f) 已修並有測試（本審查逐項讀碼確認），第 52 列只覆蓋 (c)(d)(f)。traceability.json 的 MB-48 status 為 OK，而第 52 列自述為「部分完成」（他單元三處同進程呼叫端仍用主帳號建 MemoryFacade，OPEN-MS-48-CALLERS 仍開）。兩處狀態都會讓人誤讀進度。 | 由 conductor 把第 33 列更新為已修正（寫明 (a)(b)(e) 由 ff537a7 完成，(g) 屬 ci.yml 步驟名稱、請查證是否已改），並把 MB-48 status 改為 partial 或同等值，附 OPEN-MS-48-CALLERS 引用。不需改程式。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum -a 256 對 reviewed-source-725719d9f4c4.tsv 的 20 列獨立重算（awk -F tab 取欄位） | 20 同、0 變；source-manifest.json 的 sha256 與收據 manifest 列相符（d8e95fa8…） | 收據逐位元吻合現況。HEAD 中 memory_* 檔雖經 ff537a7 提交，內容與收據一致，故本單元修正段落未被他單元改動。 |
| git diff HEAD 對 code-generation-plan.md | 無輸出（與 HEAD 位元相同）；勾選 65 勾、4 未勾，與 code-summary 新節的數字一致 | 計畫檔既有內容只有勾選字元差異（實際為零差異）；新節對計數的陳述屬實，對未勾理由的陳述部分過時（見 New Findings 第 2 列）。 |
| git diff --stat 對 backend/database.py、backend/requirements.txt | 皆為空 | 計畫 1.1、10.1、10.2 的判準現已成立。 |
| 讀碼推演 R-01、R-02、R-06 至 R-09 | 皆有對應程式與測試，且測試檔頭記有突變 | 依限制未執行任何測試；本審查不宣稱測試綠燈，只確認程式與斷言存在且形狀正確。 |
| 單元紀錄目錄是否有比 725719d9f4c4 更新的收據 | 無（目錄內最新為 725719d9f4c4，Nov 8 14:23） | 以該收據為準。 |

### Summary

收據 20 列逐位元重算全同，計畫檔與 HEAD 無差異，prior 的七項開放發現（R-01、R-02、R-06、R-07、R-08、R-09、R-13）讀碼後皆已修正並有測試鎖住，0 Critical、0 Major，判定 READY。三項 Minor：長數字 id 仍可寫出約 4300 字元的日誌行；計畫 1.1、10.1、10.2 的未勾理由已過時、可勾；merge-blockers 第 33 列與 traceability 的 MB-48 狀態欄與實況不符。15.2 與 tests_pg 的 V2、S15 仍待 CI 或本機一次性 PostgreSQL 實跑，本審查依限制未執行測試。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/user_router.py:510-517（`_blocking_user_references` 的 `memory_records`／`memory_audit_events` 兩列） | `hierarchy-data` 以 ORM 直接對 `MemoryRecord`、`MemoryAuditEvent` 做 `.count()`，繞過 `MemoryFacade`。實際影響有限：只讀、只算筆數、條件固定為「該 uid 自己的列」、用於刪除帳號前的外鍵預檢（facade 的 `Principal` 授權與 `MemoryView` 不適用此情境），沒有洩漏內容，也沒有寫入，不構成 ADR-0006 IAM 或 audit 缺口。但目前沒有任何測試或文件宣告這是「facade 唯一入口」的合法例外；`test_memory_contract.py` 只鎖 router 不得 import service，沒鎖「其他模組不得讀記憶表」。日後有人照樣在別處直接查記憶表時，這條規則就失去判準。另一個連帶後果：只要某使用者刪過任何一筆記憶，`memory_audit_events.actor_user_id`（NOT NULL FK、稽核不刪）就會讓該帳號之後永遠被擋成 409，這是 OQ-H1 規則 2 已裁決的結果，但本單元的契約沒有記載它。 | 在 `memory_facade.py` 或 `unit-test-instructions.md` 記一句：`user_router._blocking_user_references` 是 facade 唯一入口的已知例外（唯讀計數、僅本人 uid、用於刪除預檢）；並補一條靜態斷言，列舉允許直接 import 記憶 ORM 模型的模組（`memory_*`、`user_router`），讓新增者必須有意識地改清單。 | Unresolved |
| R-02 | Minor | backend/services/memory_errors.py:`class MemoryError(Exception)`；memory_facade.py:88、:502（匯入並放進 `__all__`） | 領域例外基底類別與 Python 內建 `MemoryError`（記憶體耗盡）同名。`memory_facade.py` 以同名匯入並重新匯出，任何 `from services.memory_facade import *` 或 `U11` 寫 `except MemoryError` 的人會悄悄遮蔽內建例外，或反過來抓不到真正的 OOM。目前 repo 內沒有其他模組匯入它，所以尚未造成錯誤，但 `intent-router` 修合併前必修第 13 項時正要在 `intent_routing.py` 分辨這些例外型別，是最可能踩到的人。 | 改名為不衝突的名稱（例如 `MemoryServiceError`），或保留舊名並在檔頭與 `__all__` 旁明寫「不得與內建同名使用」。屬契約型別變更，需同步通知 `intent-router`、`memory-page-ui`，故列 Minor 而非本輪必修。 | Unresolved |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/code-generation/code-summary.md §三 查驗表 Step 1.3、1.4、8.3（及 2.4、5.5、10.3 三格未勾的處理） | 重點 (c) 的判斷：三格維持未勾是誠實的，因為字面要求確實與實作不符，且偏離理由已逐格記載。但有兩個不對稱。其一，Step 1.3、1.4、8.3 的字面判準是「開工前時點檢查」或「無 git 基準可比」，本輪也標「成立（以現況判）」，改用替代判準勾選；這與 2.4、5.5、10.3 不勾的標準不一致（同樣是字面無法成立，卻一個勾一個不勾）。其二，2.4、5.5、10.3 三格都已有刻意偏離理由，卻仍以未勾懸在計畫上，閘門讀者無法一眼看出它們是「已接受偏離」還是「未完成」。 | 兩選一：(a) 把 1.3、1.4、8.3 也改為「維持未勾，替代判準成立」，與其餘三格同標準；(b) 在計畫對應步驟上就地加註「接受偏離，見 code-summary §三」並勾選。不需要改程式。 | Resolved (reviewer) |
| R-04 | Major | backend/services/memory_service.py:`scored_candidates`（取負號）、`search_records`、`create_record` 的 `UPDATE ... CAST(:embedding AS vector)`；backend/tests/test_memory_ranking.py:90（只在註解提到 `scored_candidates`） | 檢索與向量寫入這兩條核心路徑在 repo 的自動化測試裡完全沒有被執行。我 grep `tests/*.py`，`scored_candidates`、`_vector_literal`、`_supports_vector`、`SET embedding` 零個實際呼叫；`search_records` 只在 `test_memory_pending_authz` 被 mock 成回空。`scored_candidates` 的 docstring 宣稱「`rank_candidates` 的 PBT 第 2 條性質是它唯一的機械防線」，但該 PBT 餵的是任意手造分數，驗不到「距離要取負號」。把 `score=-distance` 改成 `score=distance`，ranking 會整個反過來（最不相似排最前），所有 50 個測試仍然全綠。同樣，`create_record` 在 SQLite 上跳過 `UPDATE`，PostgreSQL 上的寫入向量沒有任何測試；一旦失效，每列 `embedding` 都是 NULL，檢索永遠回空而不報錯。`verify_memory_schema.sql` 的 S15 是另一份查詢的複本，且它直接 INSERT 向量，沒有走 `create_record`，所以也驗不到這兩處。這是本單元宣稱的「唯一完全靜默的失敗模式」，卻沒有可以變紅的測試。 | 補測試讓兩處可失敗：(1) 對 `scored_candidates` 寫純單元測試，斷言距離較小者分數較大，且經 `rank_candidates` 後最近的排第一；(2) 對 `search_records`／`create_record` 加一組以 mock 或 `str(compiled)` 驗證的測試（斷言 `_supports_vector` 為真時確實送出 `UPDATE ... SET embedding`、`kinds` 與向量字面值綁定正確），或把「寫入後檢索得到」納入 `verify_memory_schema.sql` 並說明在 CI 的位置。完成後做一次突變（取負號改回、略過 UPDATE）確認紅燈。 | Resolved (reviewer) |
| R-05 | Minor | backend/services/memory_service.py:`delete_with_audit`；backend/services/memory_facade.py:`delete` | 開發者的觀察「同筆記憶併發刪除可能 500」方向不對。我用兩個 session 各自取到同一列後依序呼叫 `delete_with_audit`，實測第二次不報錯（只有 SAWarning「expected to delete 1 row(s); 0 were matched」），並且**多寫了第二筆 `deleted_by_user` 稽核**（稽核列數 2）。這違反 `BR4.3` 與 `NFR4.21` 想避免的稽核失真（`AC4.3.2`），且在 PostgreSQL 上同樣不會擋。窗口小，但屬於稽核正確性。 | 刪除時以 `DELETE ... WHERE id = :id` 檢查 `rowcount`，為 0 就回滾並丟 `MemoryNotFound`；或在稽核寫入前先 `SELECT ... FOR UPDATE`。加一個雙 session 的回歸測試。 | Resolved (reviewer) |
| R-06 | Minor | backend/services/memory_service.py:`list_records`、`SEARCH_SQL`；`functional-spec.md` 步 8 | 讀取不過濾 `expires_at`（開發者觀察屬實）。`functional-spec.md` 沒要求過濾，故不違規；但清除機制 `U9` 在 `infrastructure-design` 仍有未結項，已過 90 天的 episodic 記憶在清除前仍會被 `search` 餵進 `U11`。 | 在 `memory_service.py` 或 `code-summary.md` 明確記錄「讀取不過濾過期列，依賴 U9 清除」為已接受取捨，並指派承接站；或加 `expires_at IS NULL OR expires_at > now()` 條件並同步 S15。 | Unresolved |
| R-07 | Minor | backend/services/memory_service.py:`log_denied`；backend/services/memory_facade.py:`_authorize_approved`、`delete` | 拒絕日誌以 `%s` 原樣寫入呼叫端提供的 `memory_id`。`DELETE /records/{memory_id}` 的路徑參數是任意字串（百分比編碼的換行會被解碼），可偽造日誌行或灌入超長字串。沒有內容外洩，但 `NFR7.30` 的日誌是「有人在枚舉」的唯一偵測手段，被汙染會降低其可信度。 | 記錄前截斷長度並以 `%r` 或去除控制字元的方式輸出；補一條含換行 id 的斷言。 | Unresolved |
| R-08 | Minor | backend/services/memory_router.py:`MemoryCreateRequest.content`；memory_facade.py:`write`、`search` | `content` 與檢索 `query` 沒有任何長度上限，會直接送進 embedding 提供者並寫入 `TEXT`。已認證使用者可用超大酬載消耗 embedding 資源與儲存；`NFR7.28`／`NFR7.29` 只限列出與 `limit`。 | 在 router 加 `max_length`（並同步 `openapi.json`），或在 facade 以 `MemoryInvalidInput` 拒絕，並記錄上限值的來源。 | Unresolved |
| R-09 | Minor | backend/services/memory_facade.py:416-420（delete 內的 except MemoryNotFound 重拋）；backend/tests_pg/test_memory_service_pg.py D1 與 D2 | 競態下「以呼叫端原值重拋，使 404 detail 與一般不存在逐字相同、且不寫 reason=owner 日誌」是 [D1]=A 的對外承諾，但目前沒有任何測試走到這個分支。D1 與 D2 都直接呼叫 memory_service.delete_with_audit，繞過 facade；backend/tests 中唯一碰到 delete_with_audit 的是 A15 的 patch，且不是拋 MemoryNotFound。把這段 try/except 整段拿掉，所有測試仍全綠。因為 service 內拋的是 MemoryNotFound(str(整數 id))，只有在呼叫端傳入非正規形式（例如前導零）時兩個 detail 才會不同，所以這個缺口不構成目前的實際缺陷，也不影響本輪 (a) 至 (e)。 | 在 tests 補一支 facade 層測試：patch memory_service.delete_with_audit 拋 MemoryNotFound，斷言 facade.delete 以呼叫端原值重拋，並斷言不寫 reason=owner 日誌；順手做一次拿掉 try/except 的突變，結果記入 code-summary。 | Unresolved |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/code-generation/unit-test-instructions.md（§一表格與 §2.2、§五） | 本輪新增的 tests_pg 測試（V1、D1、D2）沒有出現在單元的測試執行說明：該檔全文沒有 tests_pg 一詞，仍把「真實 PostgreSQL 斷言」描述成只有 psql 加既有 memory-schema job。照該檔操作的人不會知道要用 DATABASE_URL 另跑 python -m unittest discover -s tests_pg，也不知道前置條件是已套用 schema_rbac.sql。計畫 Step 15.3 只列 source-manifest、traceability、code-summary，沒有列這份。 | 在 unit-test-instructions.md 補一小節：tests_pg 的三個測試、執行指令、DATABASE_URL 與 schema 前置條件，並註明 CI 由 concurrency job 執行（不是 memory-schema job）。 | Resolved (reviewer) |
| R-11 | Minor | .github/workflows/ci.yml（concurrency job 的步驟名稱「Run real-PostgreSQL concurrency tests (C1-C3)」）；merge-blockers.md 第 22 項 (e) | (e) 要求「CI 的 memory-schema job 要跑到 (b)、(c)」。CI 覆蓋是真的：memory-schema job 只跑 psql、沒有 Python，tests_pg 實際由 concurrency job 執行，該 job 用 pgvector/pgvector:pg18 加 schema_rbac.sql，discover -s tests_pg 會撿到新檔，我在本機 PostgreSQL 17 跑出 13 個全綠，與 code-summary 一致。需要誠實標註兩點：其一，步驟名稱「(C1-C3)」早已與實際測試數不符，且使 V1、D1、D2 在 CI log 裡沒有名目；其二，ci.yml 自己註明 ut 沒有任何必要狀態檢查，concurrency job 紅燈不擋合併，是訊號不是閘門，所以 (e) 在機制上成立、在強制力上不成立。code-summary 已說明 job 名稱落差，但沒有記上述兩點。 | 在 code-summary 第 22 項處置的 CI 小節補一句「訊號非閘門，需把 concurrency 加入 ut 必要檢查才不可繞過」；步驟名稱可在下次改動 ci.yml 時一併更正，不必在本單元處理。 | Resolved (reviewer) |
| R-12 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/code-generation/code-summary.md（§三 查驗表 4.3 那一列，約第 476 行） | 該列仍寫 delete_with_audit 單一 commit() 在 :495、widen_scope_with_audit 在 :523。本輪改寫後實際位置是 :527 與 :555。第 22 項處置段新引用的行號（:477-527、:511、:516-518、facade :412-420、ranking :167-240、V1 :186）我逐一核對皆正確，只有舊表格這兩個定位過期。 | 在該列加註「已因第 22 項改寫而位移，現為 :527、:555」，或更正行號。 | Resolved (reviewer) |
| R-13 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-service/code-generation/code-summary.md 第三節 R-01、R-02、R-06 至 R-09 的處置欄 | 這六項寫為由 conductor 併入 merge-blockers，但本單元紀錄本身無法證明已併入；在併入之前，它們只存在於本單元的文字裡，閘門後可能無人追蹤。 | 閘門核可後由 conductor 確實把這六項併入合併前必修清單，並讓 R-06 引用第 17 列 memory-purge 的暴露窗口。不需改程式。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-13 Not re-checked this round
