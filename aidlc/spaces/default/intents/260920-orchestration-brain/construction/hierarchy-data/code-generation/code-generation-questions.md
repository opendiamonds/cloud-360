# Code Generation 問題檔 — `U4 hierarchy-data`（`spec`）

<!-- Stage: code-generation（Construction 3.5）· Unit: hierarchy-data · kind: spec -->

## 前言

本站不問設計問題——設計已在 functional-design、nfr-requirements、nfr-design 三站定案。
本檔只承載一個關卡：**計畫核准**。

計畫與單元測試指示的摘要在下方；完整內容見
`code-generation-plan.md` 與 `unit-test-instructions.md`。

## Plan Approval

**計畫要做什麼**：三張新表的 DDL ＋ `user_diagrams.system_id` ＋ 兩個部分唯一約束
＋ `created_at` 索引（寫進 `schema_rbac.sql`）；一個可被 `unittest` 匯入呼叫的遷移入口
（`backend/services/hierarchy_migration.py`，逐使用者交易、回傳三個計數、終檢失敗即 raise）；
一支獨立執行指令（`backend/scripts/run_hierarchy_migration.py`，失敗以非零結束碼收場）；
13 個單元測試（`backend/tests/test_hierarchy_migration.py`，三個元件各 5／3／5）；
`DEPLOY.md` 的四項同步（前進步驟、回復程序、部分狀態、靜止前置）。

**方法論**：Testing Contract 解析為 **test-after**（每層先實作、再寫並跑該層測試），
`plan_profile.steps` 的 14 步採用 9 步，省略 API/endpoint 與 Frontend 兩層——
本單元交付零端點、零畫面，而 `SEC-3` 的機械檢查正是斷言那一層不存在。

**測試指令**（限定本單元，不是裸的 discover）：
`python -m unittest tests.test_hierarchy_migration -v`

**明確不做**：任何 router 或 service 層讀寫函式（`SEC-1`）、任何前端檔案、任何新環境變數
或憑證（`SEC-2`）、任何新套件或 Alembic（`D-4`）、欄位級加密與 `sslmode`（`U4-R4`）、
90 天清除的實作（`S-5` 必須走 gh-aw 或 Actions）、把 `system_id` 收成 `NOT NULL`
（`OQ-H2` 未定案，且會讓 `U4-V2` 的 CI 夾具不可構造）、改 `deploy.yml` 加有序靜止步驟（`S-9`）。

**三件計畫裡誠實寫下、你應該知道的事**：
（1）部分唯一索引在 SQLite 與 PostgreSQL 語法不同，若某約束無法在 SQLite 忠實重現，
該案例標記為只能在真實 PG 驗證並記為 open item，**不得為了讓測試變綠而弱化約束**；
（2）覆蓋率 80% 的宣告目前無法量測也無法強制（本 repo 無覆蓋率工具），
本單元的實際門檻是 13 個案例全綠 ＋ 既有 21 個測試檔維持全綠；
（3）`DEPLOY.md` 會寫進靜止前置，但**管線本身還做不到**——`deploy.yml:121–124`
用單一 `up -d --build` 一次拉起整座 stack，`S-9` 尚未落地。

[Approval Fingerprint]: sha256:v3:d8c055883bed7e15f89510a8cb5dfe6a39f3525f3fc64096d604953fdd335044
[Planned Source]: 802373aa5c6561411316256deaeb234739b9236c50689208970b23370569a01e

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
