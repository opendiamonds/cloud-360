# Functional Design — 釐清問題 · U4 `security-reviewer-permission`

> Stage: functional-design（Construction 3.1）· Unit: `security-reviewer-permission`（kind: service）· Depth: Standard
> **每題均附建議選項**，建議理由與代價寫在選項描述內。
> **成本揭露**：本題組 3 題。本站有 reviewer（`reviewer_max_iterations: 2`）。本單元為 `bolt-plan.md` 的 **B1**，是本 intent 失敗模式最隱蔽的單元。

## 已由上游定案、不重問

| 事項 | 定案來源 |
|---|---|
| 只更新、不插入 | `components.md` C-7「執行順序與空表行為」（iteration 2 Critical 修正） |
| 在既有權限種子之後執行 | 同上 |
| 以既有的「最後異動者」欄位作為套用標記，不新增表 | `components.md` C-7「冪等語意」（iteration 3 Finding M1） |
| 條件式更新而非無條件回寫 | 同上；理由是保留管理員的撤銷 |
| 需要三態記錄（已套用／已跳過／未命中目標列） | `component-methods.md` C-7「為何需要三態記錄」 |
| 授權範圍外溢（J3a 同時開兩個端點）為可接受 | requirements FR-4、stories AC-3.5，已人工確認 |
| 稽核記錄易失性不修復 | requirements C-7，記為已知限制 |

## Sources（出題前的唯讀查證，供題幹與選項引用）

| # | 查證 | 結果 |
|---|---|---|
| S1 | 目標列 | `('Security_Reviewer', 'J3a', False, False, False)` — `backend/services/rbac_seed_data.py:299`；`schema_rbac.sql:475` 為對應的 `false, false, false` |
| S2 | 兩檔規模 | **各 308 列**，皆為可機器解析的字面值 `('Role', 'Story', bool, bool, bool)` |
| S3 | 產生腳本 | **不存在**（`scripts/`、`tools/` 皆查無）。`rbac_seed_data.py` 檔頭「勿手改；改 SQL 後重跑產生腳本」的契約已失效 |
| S4 | seed 函式的三個呼叫端 | `database.py:106`（啟動，`force=False`）、`user_router.py:286`（**公開未認證**的角色目錄端點，`force=False`）、`user_router.py:824`（管理員重置，`force=True` — 刪光重寫） |
| S5 | seed 的空表判定 | `rbac.py:63-65`：`count > 0 and not force` 即 `return 0`；寫入時 `updated_by="system_seed"`（`:76`） |
| S6 | `init_db()` 的例外處理 | 整段包在 `try/except Exception → logger.error + db.rollback()`，**且不重新拋出**；`finally: db.close()` |
| S7 | 既有三個補欄補丁的形狀 | `database.py:142/189/259` 皆為 `with engine.begin() as conn:` + 逐句 `try/except` + `logger.warning`，**自行提交、不沿用外部 session** |
| S8 | `role_permissions` schema | 主鍵 `(role, story_id)`；`updated_by` 為 `String(128), nullable=True`；`updated_at` 帶 `server_default=func.now()` 與 **`onupdate=func.now()`** |
| S9 | J3a 現況 | 11 個角色中僅 `Project_Admin`／`Platform_Admin`／`Platform_Owner` 有 `view`（8 個無；本次變更後剩 7 個）；J3a:`edit` 另外把關全部變更端點（`user_router.py:481/526/566/615/662`） |
| S10 | J3a:view 守的端點 | `user_router.py:439`（使用者清單）與 `:466`（授權申請清單）—— 即已確認可接受的範圍外溢 |

---

## Q1. FR-4.3「兩處預設值同步」的一致性檢查落點

> `components.md` C-7 §FR-4.3 明文把此項交給 Construction，並要求「若判定超出範圍，須明寫以人工核對承接並登錄為已知限制，**不得留白**」。

A. **比對測試，涵蓋全部 308 列** — **（建議）**
   - 解析 `schema_rbac.sql` 的 INSERT 區塊與 `rbac_seed_data.py` 的 list，逐列比對。
   - 依 S2，兩檔都是可機器解析的字面值，**全量比對只比單列多一行 regex**。零新依賴，放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到。
   - 額外價值：依 S3，這個檔的「勿手改」契約已失效且無工具支撐，全量比對是目前唯一能鎖住它的機制。
   - 代價：日後改其他權限時忘了同步兩處會讓測試紅 —— 這正是它要做的事。

B. **比對測試，只涵蓋本次變更那一列**
   - 好處：範圍最小。
   - 代價：實作成本與 A 幾乎相同，卻只鎖住 1/308；其餘 307 列仍無防漂移機制。

C. **不寫測試，以人工核對承接**
   - 代價：本單元已有一項無自動化驗證的缺口（既有環境套用），再加一項會讓 B1 的驗收幾乎全靠人工。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. 套用補丁的落點與交易邊界

A. **`init_db()` 的 try/finally 之後，自有 `with engine.begin()` 連線** — **（建議）**
   - 依 S6，`init_db()` 整段包在 `except Exception → rollback` 且不重拋。放在該區塊**之後**有三項好處：①結構上保證在 seed 之後，順序不靠人記得；②自行提交（比照 S7 的既有補欄先例），不會被 `db.close()` 靜默丟棄；③不落在那個寬鬆的 except 裡，三態記錄不會被一句「初始化時發生錯誤」蓋掉。
   - 代價：走 Core 層 SQL 而非 ORM。

B. **try 區塊內、seed 之後，沿用同一 Session**
   - 好處：程式碼最短、與 seed 緊鄰可讀。
   - 代價：落在 `except → rollback` 範圍內；若忘記 commit 會被 `finally: db.close()` 靜默丟棄 —— 這正是 `risk-and-sequencing-rationale.md` 列為**高**嚴重度的「寫入被靜默丟棄」。

C. **定義在 `rbac.py`，緊鄰 seed 函式**
   - 好處：兩個相依函式同檔。
   - 代價：順序契約仍表達在 `database.py`（跨檔），並未因此更安全；交易語意同 B。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. 條件符合、但該列的權限值本來就已是開啟時，是否仍寫入補丁標記

A. **值已正確就不寫，保留 `system_seed`** — **（建議）**
   - 只在值確實需要翻轉時才 UPDATE 並蓋標記。全新環境（seed 已以新預設值寫入開啟）的該列維持 `updated_by='system_seed'`，如實反映「這是種子寫的，不是補丁改的」，也不會因 S8 的 `onupdate=func.now()` 白白推進 `updated_at`。
   - 代價：每次啟動多一次單列主鍵 SELECT（成本可忽略）。

B. **條件符合就更新並蓋標記**
   - 好處：後續啟動直接跳過，邏輯最單純。
   - 代價：全新環境那一列會被標成「補丁套用過」（實際是種子寫的），稽核跡象失真，且 `updated_at` 被推進。

C. Not yet defined
X. Other (please specify)

[Answer]: A
