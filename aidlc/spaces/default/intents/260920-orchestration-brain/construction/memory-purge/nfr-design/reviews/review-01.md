## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-08T00:15:25Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `security-design.md` §一之三「三道鎖」表＋§一之二 `password_hash` 列 | 設計宣稱第 3 道鎖（`password_hash` 為非 bcrypt 格式使比對「不可能回 True」）會優雅失敗，但已實地以本 repo 的 `bcrypt` 套件（`requirements.txt` 的 `bcrypt`／`passlib[bcrypt]`，本機解析版本 5.0.0）驗證：`bcrypt.checkpw(plain, non_bcrypt_hash)` 不是回傳 `False`，而是**丟出 `ValueError: Invalid salt`**。`user_router.py:397-411` 的 `login()` 呼叫 `verify_password()`（`auth.py:37-40`，`bcrypt.checkpw` 外無 `try/except`）且端點本身也無包覆，`main.py` 未註冊全域例外處理器（`FastAPI(title=...)`、無 `debug`／`exception_handler`）。故任何人以該哨符 `username` 嘗試登入（任意密碼）會觸發**未處理的例外**，FastAPI 預設回應為 500，而非設計所稱的乾淨拒絕。這不構成登入繞過（帳號仍登不進去），但違反 `construction.md` 的「Errors must be surfaced ... distinguish recoverable vs fatal」——未捕捉的例外是意外的致命路徑，且該哨符 username 本身已因 `OPEN-ND9-1`（出現在 Admin 清單）可被得知，使這條路徑可被外部觸發並產生持續的 500 噪音／未分類錯誤日誌。 | 在 `security-design.md` §一補一句：password_hash 的哨符值必須是**語法上有效的 bcrypt 格式**但內容上不可能比對成功（例如對一個固定但不可得知的隨機明文做真正的 `bcrypt.hashpw`），或要求 `code-generation` 在呼叫路徑加 `try/except ValueError` 並視為驗證失敗。兩者皆可，但本站的「三道鎖都不是本單元新寫的程式／任何一道被繞過都不是本單元回歸」這句需要收回，因為第 3 道鎖目前的具體取值方式會在既有程式上產生一條新的未處理例外路徑。 | New |
| R-02 | Minor | `security-design.md` §三之一（順序）＋ §三之二（交易邊界） | §3.1 為「先寫稽核、再刪記憶」給出的理由是「反過來（先刪再寫）若在中間失敗，記憶已消失而稽核不存在」，但 §3.2 同一份文件宣告步 1＋步 2 是**同一個交易**。在單一資料庫交易內，陳述語句的先後順序不影響原子性——交易失敗即整個回滾，不論 INSERT 寫在 DELETE 之前或之後，都不會出現「只有一半生效」的半套狀態。故 §3.1 給出的「順序防止部分失敗」論證在 §3.2 的交易邊界之下是**站不住的**（結論本身不受影響：無論語句順序如何，同交易都安全），但論證的因果關係錯誤，可能誤導日後的實作者以為「語句順序」才是安全性的來源而非「交易邊界」。 | 修正 §3.1 的論證：改寫為「語句順序對同交易內的原子性無影響；之所以仍選擇『先寫稽核、再刪記憶』的語句順序，純粹是為了讓程式碼的敘事對應 `FR4.7` 的因果順序（先有紀錄、後有刪除），不是安全性的必要條件」，或刪除該因果論證、只保留交易邊界作為唯一的安全性來源。 | New |
| R-03 | Minor | `security-design.md` §一之二～之四（系統 actor seed）＋ `project.md ## Mandated`（schema_rbac.sql 可重跑安全寫法） | 設計多次強調 DDL 的 `IF NOT EXISTS` 可重跑性（§一之五第 2 項引用 `project.md` 的 blocking 同步規則），但系統 actor 的**seed INSERT 本身**從未以任何形式（即使是「設計意圖示例」）展示其可重跑寫法。`project.md ## Mandated` 逐字要求 `schema_rbac.sql` 的新增內容「使用 IF NOT EXISTS 等可重跑安全寫法」；`DEPLOY.md:336`／`:638` 證實既有環境（如 `192.168.10.10`）取得 schema 變更的唯一路徑是手動重跑整支 `schema_rbac.sql`，而非走 `docker-entrypoint-initdb.d`（後者只在空 data volume 執行一次）。一個不帶 `ON CONFLICT (username) DO NOTHING` 或等價寫法的 `INSERT INTO users (...)`，在既有環境重跑整支腳本時會因 `ix_users_username` 的 UNIQUE 約束而整段失敗，擋下同一支腳本裡其後的所有陳述（包含本次要新增的其他 DDL）。 | 在 §一補一條：系統 actor 的 seed 寫法必須是 `INSERT ... ON CONFLICT (username) DO NOTHING`（或等價的「先查不存在才插入」寫法），並註明這是既有環境可安全重跑整支 `schema_rbac.sql` 的必要條件，呼應 `project.md` 對本檔新增內容的硬性要求。 | New |

### 摘要

- `new-design-problem`：3（R-01、R-02、R-03 全部是本站這一輪才做出的具體決定〔哨符密碼雜湊格式、順序論證、seed 寫法〕所暴露的缺口，不是上一站遺留或跨單元傳播而來）。
- `pre-existing-unreviewed`：0。
- `propagated-from-upstream`：0。
- 總計：3 項（1 Major、2 Minor）。依團隊驗收規則（零 Critical、≤2 Major 即 READY），本站判定 **READY**；R-01 雖為 Major 但不構成安全繞過（帳號仍無法登入成功），只是錯誤處理路徑不如設計所述優雅，且修法成本低（換一個仍非 bcrypt 但語法合法的哨符值，或補一個 `try/except`），不阻擋本站交付。

### 覆蓋範圍

**已查證（有機械證據，逐一開檔或實際執行）**：
- `[ND1]`=A 三道鎖的三個引用（`auth.py:75`、`rbac.py:54-55`、`password_hash` 非 bcrypt）全部逐行開檔核對，行號與內容皆準確；另外核對了 `login()`（`user_router.py:397-420`）**也**獨立檢查 `is_active`（第 2 道鎖在登入路徑與既有驗證路徑〔`get_user_from_token`〕各有一份，彼此一致、互為備援）。
- 第 3 道鎖的「不可能比對成功」主張，以本機已安裝的 `bcrypt`（5.0.0，與 `requirements.txt` 一致）實際呼叫 `bcrypt.checkpw()` 驗證，發現它是丟例外而非回 False（R-01 的證據）。
- `[ND1]`=A 的「以 username 查 id、不寫死整數」：`users.id` 為 `SERIAL`、`ix_users_username` 為 `UNIQUE`，兩者皆開檔核對（`schema_rbac.sql:73`）。
- `[ND2]`=A 的三項實測（`deploy/docker-compose.deploy.yml` 只設三個環境變數、`schema_rbac.sql:524` 的 `GRANT ... TO current_user`、官方 postgres image 行為）與本站文字逐字一致；§四 ADR-0006 表與上一站 `nfr-requirements/security-requirements.md §四` 逐格比對，三格（IAM／Encryption／Network exposure）判定一致，IAM 格的差異有明確理由（非靜默覆蓋）。
- `NFR8.10`「選 B 會打破零新部署設定」的推論：核對 `project.md` 的 `render-env.sh`／`.env.example`／compose 三處同步 blocking 規則，推論成立。
- `traceability.json`：14 條 `upstream_ids` 全數有對應 `coverage` 項，6 條 `N/A` 項的理由（編號佔用表副作用）合理且與上一站 `security-requirements.md §一` 的敘述一致；5 項 `reverse` 對應 `nfr-requirements/reviews/review-01.md` 的 `R-01`／`R-02`／`R-03` 逐項核對內容一致，無誤記。
- `/api/auth/list` 的既有端點（`user_router.py:510-545`）：確認 `total = db.query(User).count()`（無過濾）與分頁查詢皆不排除系統 actor 列，證實 `OPEN-ND9-1` 的風險描述準確且略為低估（不只是「清單上多一列」，`total` 計數也會永久 +1）；但這是已揭露風險的延伸細節，不升級為新發現。
- e2e 回歸測試交叉檢查：`frontend/tests/e2e/regression.spec.ts` 的「測試環境只有 admin 一個已核准帳號」假設（用於角色切換測試）與 `user_router.py` 的 `admin_edit_count` 迴圈皆過濾 `is_active == True`，系統 actor 列（`is_active = FALSE`）不會被計入，故不破壞該既有測試的前提——查證後確認無新回歸。
- `schema_rbac.sql` 的既有環境遷移路徑（`DEPLOY.md:336`／`:638`）與可重跑寫法要求，核對後發現 R-03。

**本輪未查證／超出範圍**：
- `OPEN-ND9-2`（是否新增受限資料庫角色）與 `OPEN-N9-1`（`NFR7.13` 偵測機制）本身的可行性——本站與上一站一致指派給 `infrastructure-design`，不在本站 `packaging` kind 的職責內，故未深入評估。
- 未實際啟動 Postgres 容器重現 `GRANT ... TO current_user` 與官方 image 的 superuser 行為（僅以官方文件與既成事實推理驗證，與 `nfr-requirements` 審查的查證方式一致）。
- `code-generation` 階段尚未存在，故未能驗證 R-01／R-03 所指的例外路徑與 seed 寫法在實際實作中是否會被自然修正（例如實作者可能自行選用合法 bcrypt 哨符值）；本站僅評估**設計文件當前寫法**是否已明確排除這兩個風險，結論是尚未排除。

VERDICT: READY
