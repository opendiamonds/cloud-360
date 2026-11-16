# 安全設計 — `U20 requirement-field-service`

> 本檔是本站的審查標的。它把 `security-requirements.md` 的 `NFR20.7`–`NFR20.14` 與
> `NFR8.120` 具體化，並落實上一站審查（`nfr-requirements` 的 `review-01`）中屬設計層的
> R-01、R-06、R-07。

## 一、資料分類（承 `review-01` R-07 更正）

欄位值為**內部（業務機密）**：SLA、預算、計費區域等架構假設。上一站寫「不含 PII、憑證或
token」，那是**設計上不預期**而非可保證——欄位是自由文字，使用者或代寫的 agent 都可能填入
任何內容。處置：

- 不宣稱保證；不新增加密或遮罩（沿用既有 PostgreSQL volume 與 Cloudflare Tunnel TLS）。
- log 永不記值（`NFR20.27`／`NFR20.28`），使意外填入的機密內容不會擴散到範圍更寬的 log。
- 欄位定義帶一句填寫提示「請勿填入密碼、金鑰或個人資料」，由 `U23` 顯示（交接 `OPEN-RF20-9`）。

## 二、授權：九列 allow／deny 矩陣（`NFR20.8`，承 `review-01` R-01）

角色例子取自 `rbac_seed_data.py:349-359` 的 `K4` 列（欄序 view／edit／review）：有 `K4.edit`
的是 `Project_Architect`、`Project_Editor`、`Project_Admin`、`Platform_Admin`；只有 `K4.view`
的是 `Developer`、`FinOps_Analyst`、`Security_Reviewer`、`Platform_Owner`；兩者皆無的是
`SRE`、`Ops_Lead`、`Platform_Engineer`。

| # | 呼叫者 | `GET` | `PUT` | `DELETE` | 防的是哪個錯誤實作 |
|---|---|---|---|---|---|
| ① | 已核准、成員（`member`）、`Project_Editor` | 200 | 200 | 200 | 正常路徑 |
| ② | 已核准、**非成員**、`Project_Editor`（有 `K4.edit`） | 403 | **403** | **403** | **寫入路徑跳過成員判定**（上一站矩陣漏掉的那一列） |
| ③ | 已核准、成員、`Developer`（只有 `K4.view`） | 200 | 403 | 403 | 寫入只檢查成員、不檢查全域 `edit` |
| ④ | 已核准、成員、`SRE`（無 `K4.view`） | 403 | 403 | 403 | 讀取只檢查成員 |
| ⑤ | 已核准、成員（`project_admin`）、`Developer` | 200 | 403 | 403 | 誤以為 `project_admin` 可越過全域層（`[FD4]`=A：per-project 角色不區分讀寫，全域層決定寫入） |
| ⑥ | **待核准**、成員、`Project_Editor` | 403 | 403 | 403 | 待核准檢查遺漏（`BR41.1`） |
| ⑦ | 已核准、`Project_Editor`，系統**不存在** | 404 | 404 | 404 | 存在性判定錯置 |
| ⑧ | 已核准、`SRE`，系統**不存在** | 403 | 403 | 403 | 記下實際順序：全域層先於存在性（`BR41.2` → `BR41.3`），故無 `K4.view` 者看不到 404 |
| ⑨ | 已核准、成員、`Developer`，帶 `on_behalf_of=cost` | — | 403 | — | 代寫標示授予權限（`NFR20.9`） |

突變驗證（code-generation 必做）：拿掉 `BR41.4` 的成員判定 → ② 紅；拿掉全域 `edit` 檢查 →
③⑤⑨ 紅；拿掉 `BR41.1` → ⑥ 紅。

## 三、身分與請求本體（`NFR20.10`，承 `review-01` R-06 的使用者裁決）

- `updated_by` 只取自 `get_current_user` → `mint_principal` 的 `principal.user_id`。
- `PUT` 本體模型為 `{ value: str, on_behalf_of: str | null }`，設定 `extra="forbid"`：
  **本體帶 `updated_by`（或任何未知欄位）→ 422**。使用者已於 2026-10-12 同意此設計。
- 該 422 走 `BR46.4` 的統一形狀，不回顯輸入（見第五節）。

## 四、依賴失敗即拒（`NFR20.11`）

facade 呼叫 `HierarchyFacade`／`MembershipFacade` 時，**只捕捉**已知的領域例外並轉換
（`HierarchyNotFound`／`HierarchyForbidden` → `RequirementFieldNotFound`；`MembershipNotFound`
→ `RequirementFieldNotFound`）。**其他例外一律不捕捉**、向上傳播成 500——不得寫成
`except Exception: allow`。測試形狀見 `reliability-design.md` 第四節。

## 五、錯誤回應（`NFR20.14`，`BR46.3`／`BR46.4`）

- 領域例外由本 router 的 handler 轉成 `{ "detail": { "code": <類別>, "system_id"?, "agent_group"?, "field_key"? } }`；不含例外原文、不含值。
- 框架的請求驗證錯誤（本體形狀、路徑參數非整數、JSON 解析失敗）以**僅掛在本 router 的**
  處置轉成同一形狀（`code: "validation"` ＋ 出錯欄位名），不回顯輸入值。不改動全域
  exception handler——那會改變其他既有端點的 422 形狀。
- 三個路由的 `responses` 一致宣告 403、404、422（承 functional-design `review-02` R-04）。

## 六、輸入驗證與 SQL（`NFR20.12`／`NFR20.13`）

- 組、key、代寫組以程式內定義的集合比對（白名單），比對發生在授權之後、任何寫入之前。
- 值以 `strip()` 後計長度，> 2000 → 422。
- 全部資料存取經 SQLAlchemy 建構式與綁定參數；`ON CONFLICT` 的衝突目標以欄位物件指定，不組字串。

## 七、部署設定（`NFR8.120`）

零新環境變數。`schema_rbac.sql` 的 `J)` 區塊變更與 `DEPLOY.md` 2.2.9 的說明在**同一個
commit**；`DEPLOY.md` 要補的是一行欄位說明（agent 組識別字、刻意不帶外鍵、null 代表使用者
自填），以及收斂敘述的重跑行為。

## 八、ADR-0006 四面向

與 `security-requirements.md` 第六節一致，逐格比對無相反：IAM 適用（第二～四節）；
Encryption 與 Network exposure 適用但不在本單元（無新傳輸路徑、無新監聽埠）；
Audit logging 適用（資料列溯源欄位＋拒絕 log，見 `observability-design.md`）。
