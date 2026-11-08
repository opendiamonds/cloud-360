## Review
**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

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

> R-01 Reviewer note: user_router.py:29-30 仍直接匯入 MemoryAuditEvent、MemoryRecord，:512 與 :517 直接 count()；仍無文件宣告的例外，也無允許清單斷言。屬已知限制，不影響本輪程式碼行為，維持 Minor。

> R-02 Reviewer note: memory_errors.py:51 仍為 class MemoryError(Exception)，memory_facade.py:88 匯入、:508 重新匯出。契約型別更名需通知 intent-router 與 memory-page-ui，維持 Minor。

> R-03 Reviewer note: 計畫 1.3、1.4、2.4、5.5、8.3、10.3 六格皆已勾選並就地加註接受偏離與理由，標準一致，且註記如實揭露偏離，例如 5.5 寫明實際為五條路由、2.4 寫明 models.py 有四條 CHECK。不是把未完成偷渡成已完成。

> R-06 Reviewer note: memory_service.py 的 expires_at 仍只出現在 SEARCH_SQL 欄位 :90、建立 :235 與映射 :369，讀取不過濾過期列。仍是已知限制，依賴 U9 清除。

> R-07 Reviewer note: memory_service.py:651 仍以 %s 原樣寫入 memory_id，無截斷也無控制字元處理。

> R-08 Reviewer note: memory_router.py 全檔 max_length 命中 0，content 與 query 仍無長度上限。

> R-09 Reviewer note: memory_facade.py:416-420 的 except MemoryNotFound 重拋分支仍無任何測試走到。

> R-10 Reviewer note: unit-test-instructions.md §2.2a 已列 tests_pg 的三個測試、指令、DATABASE_URL 與 schema 前置條件，並註明由 concurrency job 執行。

> R-11 Reviewer note: code-summary 第 22 項處置的 CI 小節已補訊號非閘門一句，並記步驟名稱 C1-C3 留待更正。

> R-12 Reviewer note: code-summary 第 476 行 4.3 列已加註位移，現行 memory_service.py:527 與 :555，我以 grep 複核 commit() 位置相符。

### Validation Tool Results
| Tool | Result | Interpretation |
|---|---|---|
| 重放 DEPLOY.md hunk 搜尋 search.py，以 624c170 版為底、現況為目標、收據雜湊 2608a131 | MATCH：還原 hunk 3、17、18 即逐位元等於收據 | 收據之後只多了三個 hunk，我獨立重現。hunk 3 位於 DEPLOY.md:730-738，是 U18 三表的誠實代價段；hunk 17 在 :2229，hunk 18 在 :2239，皆為 U14 入口頁的 6a 回滾描述。三者都不涉及記憶 schema、HNSW 索引或 memory-schema 驗證，與本單元無關。 |
| 逐檔 shasum 比對最新收據 reviewed-source-3a2419efee6d.tsv | 全部相符 | 目前工作樹與本輪送審收據一致。比對舊收據 e6f8d2194126 則只有 DEPLOY.md 不同，與 code-summary 所述一致。 |
| 暫存區副本執行 unittest：test_memory_contract、test_memory_ranking、test_memory_authz，副本含 schema_rbac.sql | Ran 43 tests，OK | 與 code-summary 與 review-04 的 43 相符。未在 repo 內執行，未產生 .hypothesis 或 .pyc。 |
| 對照 DEPLOY.md 的 :250 總表 I 列、:1182 的 2.2.12 節、:591-592 的 memory-schema job | 位置與 code-summary 引用一致 | 本單元引用段落未受影響，Step 7.5 的 :1176 位移到 :1182 屬收據前的位移，內容不變。 |
| 計畫勾選數 grep | 已勾 59，未勾 0 | 與 code-summary 第七節的重勾紀錄相符。 |

### Summary
共用檔 DEPLOY.md 新增的三個 hunk 與本單元無關，43 個單元測試在副本上全綠，勾選全 59 格有據，接受偏離的註記屬誠實揭露。code-summary 的計數與行號經抽查皆屬實。剩餘的前輪發現皆為已知限制的 Minor，無 Critical 或 Major，故判 READY。
