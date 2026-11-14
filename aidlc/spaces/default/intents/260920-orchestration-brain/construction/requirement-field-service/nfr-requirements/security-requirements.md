# 安全需求 — `U20 requirement-field-service`

> 本檔是本站的審查標的。`NFR20` 的 parent id 理由見 `performance-requirements.md` 檔頭。

## 〇、上游依據

| 依據 | 內容 |
|---|---|
| 本單元 functional-design（`review-02` READY） | `BR41.1`–`BR41.6` 授權、`BR42.1`–`BR42.5` 驗證、`BR45.1`–`BR45.5` 溯源、`BR46.1`–`BR46.4` 錯誤、`BR47.1`–`BR47.4` 資料表變更 |
| `K-17` | 唯一授權入口 `RequirementFieldFacade`；per-project 判定委由 `K-16`；拒絕拋 `RequirementFieldForbidden(story_id='K4', …)` |
| `FR12.6` | 兩層串聯：全域與 per-project，任一層不過即拒 |
| `FR11.6` | agent 不得做使用者不能做的事；稽核主體為使用者本人 |
| `team.md` 測試底線 A／B | 新端點須 `TestClient`；授權相關須 allow／deny 雙向 |
| `rbac_seed_data.py:349-359` | `K4` 的 11 角色列（欄序 view／edit／review）：view 為真者 8 個、edit 為真者 4 個（`Project_Architect`、`Project_Editor`、`Project_Admin`、`Platform_Admin`） |

## 一、資料分類

| 資料 | 分類 | 理由 |
|---|---|---|
| 欄位值（SLA、尖峰 TPS、預算上限、計費區域等） | **內部（業務機密）** | 是專案的架構假設與預算，不是個資；外洩的傷害是商業性的，不是個人性的 |
| `updated_by` | 內部 | 使用者 id，系統內本來就可見於成員頁 |
| `updated_on_behalf_of` | 內部 | agent 組識別字（`[FD1]`=A），非個資 |

**不含 PII、憑證或 token。** 故沒有新的加密、遮罩或保存期限要求；at rest 沿用
既有 PostgreSQL volume，in transit 沿用既有的 Cloudflare Tunnel TLS 與 nginx 反向代理。

## 二、授權（本檔的主體）

| id | 需求 | 二元判準（`TestClient`，`team.md` 規則 A＋B） |
|---|---|---|
| **`NFR20.7`** | 三個端點的授權順序與拒絕行為依 `BR41.1`–`BR41.5`，且**判定先於任何欄位讀寫** | 每個拒絕案例中，對 `system_requirement_fields` 的查詢數為 0（同 `NFR20.1` 的計數器） |
| **`NFR20.8`** | **allow／deny 雙向矩陣**，每列皆須有測試：① 已核准、該專案成員、角色有 `K4.view` → `GET` 200；② 同上但非該專案成員 → 403；③ 該專案成員、角色只有 `K4.view`（如 `Developer`）→ `PUT`／`DELETE` 403、`GET` 200；④ 該專案成員、角色有 `K4.edit`（如 `Project_Editor`）→ `PUT`／`DELETE` 200；⑤ 角色無 `K4.view`（如 `SRE`）且為成員 → `GET` 403；⑥ 待核准帳號（有角色、是成員）→ 三端點皆 403；⑦ 不存在的系統 → 404 | 七列各至少一個案例且全綠；並以突變驗證：拿掉 `BR41.4` 的成員判定時 ② 變紅、拿掉 `BR41.1` 時 ⑥ 變紅 |
| **`NFR20.9`** | 代寫標示**不授予任何權限**（`BR45.4`） | 案例：`Developer`（只有 view）帶 `on_behalf_of=cost` 寫入 → 403 |
| **`NFR20.10`** | `updated_by` 只能由伺服器自已驗證身分取得；請求本體不得能指定它 | 本體帶 `updated_by` 欄位的 `PUT` 被拒（422，形狀依 `BR46.4`），或該欄被忽略且落地值為呼叫者本人——兩者擇一，由 code-generation 定並以測試鎖住 |
| **`NFR20.11`** | facade 對 `MembershipFacade`／`HierarchyFacade` 的依賴失敗時**一律拒絕**，不得因例外而放行 | 案例：以 mock 讓 `resolve_project_role` 拋非預期例外 → 請求不為 2xx，且無任何寫入 |

**已揭露、不在本單元關閉的殘留**：

- **`OPEN-RF20-1`**：代寫標示可被自填。`NFR20.9` 保證它不影響授權，但「真的是大腦
  發起」需要 `U21` 的 agent 身分機制（`OQ-15`）。
- **`review-02` R-03**：`BR42.5` 只保護有帶 `on_behalf_of` 的呼叫；agent 路徑省略它時，
  空值寫入仍會被當成使用者清空。承接者為 `U21`／`U13`，已列入 code-generation 計畫。
- **`U15` 審查的 R-05**：`HierarchyFacade`／`MembershipFacade` 自身沒有待核准檢查。本單元
  以 `BR41.1` 在自己的 facade 第一行補上，**不依賴**下游兩個 facade 擋待核准帳號。

## 三、輸入驗證與輸出

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR20.12`** | `agent_group`／`field_key` 以程式內定義為白名單（`BR42.1`／`BR42.2`）；`on_behalf_of` 同（`BR42.3`）；`value` 去空白後 ≤ 2000 字（`BR42.4`） | 錯綁別組、未知組、超長值、未宣告的代寫組各一個 422 案例 |
| **`NFR20.13`** | 所有資料存取經 ORM 參數化，不組字串 SQL | 本單元新增檔案中無以 f-string 或 `%` 組出的 SQL 字串 |
| **`NFR20.14`** | 錯誤回應不含例外原文、不含欄位值（`BR46.3`），框架產生的 422 也一樣（`BR46.4`，範圍依 `review-02` R-04 擴到三個路由的路徑參數與 JSON 解析） | 送一個含唯一字串的超長 `value`，回應本體不含該字串；送非整數 `system_id`，回應形狀與領域 422 相同 |

## 四、部署設定完整性（承接上游 `NFR8`）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR8.120`** | 本單元**零新環境變數**；資料表變更（`BR47.1`）觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步，兩者在同一個 commit 內完成 | `validate_env_contract.py` 通過；`git diff` 中 `schema_rbac.sql` 的 `J)` 區塊與 `DEPLOY.md` 2.2.9 同時有變更 |

## 五、STRIDE

| 威脅 | 本單元的情境 | 處置 |
|---|---|---|
| **S** 偽冒 | 以他人身分寫入；agent 偽稱代寫 | 身分只取自 `get_current_user` 與 `mint_principal`（`NFR20.10`）；代寫標示僅是標示（`NFR20.9`），殘留見 `OPEN-RF20-1` |
| **T** 竄改 | 非成員或無 `edit` 者改值；錯綁到別組 | `NFR20.8` 雙向矩陣；`NFR20.12` 白名單 |
| **R** 否認 | 「不是我清的」 | 每列記 `updated_by`／`cleared_at`（`BR45.1`、`BR43.7`）；只保留最新一筆是 `ADR-015` 已接受的代價 |
| **I** 資訊洩漏 | 非成員讀到別專案的預算；錯誤訊息帶出值；系統 id 存在性探測 | `NFR20.8` ②；`NFR20.14`；存在性探測為已揭露殘留（`BR41.3` 的 note：只能探出「某 id 的系統存在」，取不到內容） |
| **D** 阻斷服務 | 大量寫入或超大本體 | 值長度上限（`NFR20.12`）；回應大小有可算上界（`performance-requirements.md` 第四節）；無獨立限流——與既有端點一致，本輪不新增 |
| **E** 權限提升 | 只有 view 的角色寫入；待核准帳號存取 | `NFR20.8` ③⑥；`NFR20.11` 依賴失敗時拒絕 |

## 六、ADR-0006 四面向

承 `unit-of-work.md` 修訂 4 與本單元 `functional-spec.md` 第七節的判定，**不重判適用性**，
只寫本站的落點；逐格比對上游判定欄，無一格相反。

| 面向 | 判定 | 本站落點 |
|---|---|---|
| **IAM** | 適用 | `NFR20.7`–`NFR20.11` |
| **Encryption** | 適用（不在本單元） | 本單元不經手 token、不新增傳輸路徑；資料分類為內部，沿用既有 at rest／in transit 保護（第一節） |
| **Network exposure** | 適用（不在本單元） | 零新進程、零新監聽埠；新 router 掛在既有 `/api` 之下 |
| **Audit logging** | 適用 | 列上的 `updated_by`／`cleared_at`／`updated_on_behalf_of`；拒絕 log 見 `observability-requirements.md` |

**PBT hard constraint**：不適用——與 `functional-spec.md` 第七節及上游一致；本單元不屬
IaC generator、cost calculator、agent routing。
