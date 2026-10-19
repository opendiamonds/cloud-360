## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本補審針對凍結的 `nfr-design/security-design.md`。設計的主幹成立：系統 actor 的外鍵缺口、`NFR6.10` 恆真的更正、ADR-0006 四面向逐格對照上游、先稽核後刪除的交易邊界，都有查證支撐，已落地的 `schema_rbac.sql`、`DEPLOY.md` 與 `memory-retention-purge.yml` 也與之相容。主要問題是凍結的設計文字與已落地程式互相矛盾，而程式才是對的：前次 review-01／review-02 提出的 R-01（非 bcrypt 哨符）與 R-03（seed 可重跑）仍留在凍結產出裡，實作已自行修正（有效 bcrypt 雜湊、`ON CONFLICT (username) DO NOTHING`、大寫 username），但設計文字未更正，下游若照設計實作會重現缺陷。另有一項 `OPEN-ND9-1` 的致命失敗模式沒有具體承接者。依規則（0 Critical、2 Major）判 READY，但兩項 Major 建議在關卡上處置。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/memory-purge/nfr-design/security-design.md` §1.2（`username`、`password_hash` 兩列）、§1.3 第 3 道鎖與其下「三道鎖都不是本單元新寫的程式」、§1.4 SQL 示例；對照 `schema_rbac.sql:836-860` 與 `backend/services/user_router.py:403` | 前次 review-01／review-02 的 R-01 已提出，仍留在凍結產出：設計規定 `password_hash` 為「非 bcrypt 格式」使比對不可能成功，但 `bcrypt.checkpw` 對非 bcrypt 值是丟 `ValueError` 而非回 False，會把未認證請求變成 500。設計另規定 username 為小寫 `system.retention-purge`，而 `user_router.py:403` 的登入查詢是 `request.username.lower()`，小寫哨符會被登入路徑直接命中，與非 bcrypt 雜湊合起來才會觸發該 500。已落地的 seed 用大寫 `SYSTEM.retention-purge`（登入查詢轉小寫後永遠比對不到）與有效 bcrypt 雜湊，並在 COMMENT 與 `schema_rbac.sql` 註解中明說「四道鎖」，等於實作已修正設計。**設計文字是錯的，落地程式是對的。** 同時「三道鎖」與實作的「四道鎖」數目不一致。 | 以 corrections 檔或就地修訂更正：username 採大寫（或任何登入轉小寫後比對不到的值）、`password_hash` 為有效 bcrypt 雜湊（對從未記錄的隨機明文），鎖數改為四道並收回「三道鎖都不是新寫的程式」「任何一道被繞過都不是本單元回歸」兩句；§1.4 的 SQL 示例同步改為實際的查詢鍵。 | New |
| R-02 | Major | `construction/memory-purge/nfr-design/security-design.md` §1.5 第 1 點與 §五 `OPEN-ND9-1`；對照 `backend/services/user_router.py:510`（`GET /list`）、`:758`（`DELETE /{user_id}`）、`:652`（`PUT` 啟用／停用）、`:804`（`PUT /{user_id}/role`） | 設計自己寫明：刪掉系統 actor 列會使每次清除的稽核 INSERT 外鍵違反、整個交易中止、保存期不再前進，卻把處置推給「`U19`／既有端點，或後續 intent」，沒有具名承接者。實查既有端點：`GET /list` 不排除該列（`total` 也永久多一），`DELETE /{user_id}` 與角色、啟用狀態的 `PUT` 沒有針對保留 actor 的防護。本單元是 `packaging` kind，不改端點無可厚非，但這是本設計唯一能讓 90 天保存期靜默停擺的單點，且由管理者一次誤刪即可觸發；失敗雖是大聲的（workflow 非零碼），但只有在 `NFR7.13` 偵測機制（`OPEN-N9-1`，同樣懸空）存在時才會被人看到。 | 在關卡上要求把 `OPEN-ND9-1` 指派給具名承接者（單元或後續 intent），並寫明在承接前的緩解（至少 `DEPLOY.md` 警語已有，需確認 Admin UI 不提供對該列的刪除操作，或在刪除端點加保留 actor 防護）；承接站若為 `CONDITIONAL` 須附轉移目標。 | New |
| R-03 | Minor | `construction/memory-purge/nfr-design/security-design.md` §3.1 順序表與其後說明；前次 review-01／review-02 的 R-02 已提 | §3.1 以「反過來若中間失敗則記憶已消失而稽核不存在」論證先寫稽核的順序，但 §3.2 宣告步 1＋2 同一交易，交易內語句順序不影響原子性，因果論證不成立（結論仍安全）。步 3 列另有自相矛盾：先寫「必須在步 1 之後」，又寫「放在步 1 之前效果相同」。已落地的 workflow 註解已把 BEGIN/COMMIT 放在 `.sql` 檔內，交易邊界才是安全來源。 | 更正 §3.1：順序僅為對應 `FR4.7` 的敘事因果，安全性來自單一交易；刪除步 3 的自相矛盾句。 | New |
| R-04 | Minor | `construction/memory-purge/nfr-design/security-design.md` §一（系統 actor seed 的寫法）；前次 review-01／review-02 的 R-03 已提 | 設計未要求 seed 以可重跑寫法（`ON CONFLICT (username) DO NOTHING`），而 `project.md` 要求 `schema_rbac.sql` 新增內容可重跑，既有環境升級靠重跑整支腳本。已落地的 `schema_rbac.sql:857-860` 已有 `ON CONFLICT`，且註解說明了單一交易下重跑的失敗模式，所以屬設計文字落後於實作，而非實作缺陷。 | 在 §一補上 seed 必須冪等及其理由，與已落地寫法一致。 | New |
| R-05 | Minor | `construction/memory-purge/nfr-design/security-design.md` §二之二（`NFR6.10` 保留要求）、§五 `OPEN-CG5-1` | 契約端點三問：`NFR6.10` 保留的判準是「workflow 的 `psql` 呼叫不含 `-U` 覆寫」，但該判準由誰檢查（誰讀）沒有指名——設計承認無機械強制，只靠審查。`memory-retention-purge.yml` 已落地，但沒有任何 CI 步驟斷言「不含 `-U`」。恆真需求更正為弱判準後，仍是人工審查項。 | 在設計中指名驗證者（例如 code-generation 審查清單或 `validate_*` 腳本新增一條 grep 斷言），或明記「僅人工審查」並由關卡接受此風險。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 逐行核對 `auth.py:75`、`rbac.py:54-55`、`schema_rbac.sql` 的 `actor_user_id`／`ck_memory_audit_events_action` | 引用內容與行為屬實；`schema_rbac.sql` 行號因後續增修已偏移（例如 COMMENT 位於約 `:542`），設計引用的 `:484`、`:509`、`:524` 需以現檔重核 | 事實對、定位部分過期；歸入 R-01 的更正一併處理 |
| 設計 vs 落地 seed（`schema_rbac.sql:810-860`） | 大寫 username、有效 bcrypt、`ON CONFLICT` 皆與設計文字不同 | 落地對，設計錯（R-01、R-04） |
| `/api/auth/list`、`DELETE /{user_id}` 保護檢查 | 無針對保留 actor 的排除或防護 | 證實 `OPEN-ND9-1` 風險（R-02） |
| 測試、lint、建置 | 未執行（brief 禁止會寫檔的指令） | 非驗證範圍 |

### ADR-0006 四面向

IAM（`NFR6.10` 恆真之更正、系統 actor 零權限）、Encryption（無增量，哨符雜湊非機密）、Network exposure（`db` 無 host port，零增量）、Audit logging（`NFR7.11`、`NFR7.15`、先稽核後刪）皆有落點，與上游 §四 逐格一致，差異已明列理由。PBT 判定 N/A（非豁免），合理。
