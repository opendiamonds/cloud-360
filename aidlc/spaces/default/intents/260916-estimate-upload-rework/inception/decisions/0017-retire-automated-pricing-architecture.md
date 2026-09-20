# ADR 0017: 廢止 C1 自動取價架構的五條規則層約束，改以上傳估價表為唯一價目來源

- Status: Accepted（2026-09-16 同日經 §8 自我修訂；§1 與 §3 須連同 §8 一併閱讀，不得單獨引用）
- Date: 2026-09-16（本檔建立於 2026-09-16T06:55:21Z，§8 追加於 2026-09-16T07:20Z，皆讀自 `date -u`）
- 節數：**8**
- Amends: **`aidlc/spaces/default/memory/project.md`** 的 `## Forbidden` 第 79 行與第 83 行、`## Mandated` 第 120 行；**`aidlc/spaces/default/memory/team.md`** 的 `## Code Style` 第 196 行與第 198 行。五條原文皆保留於各該檔案，本 ADR 只限定其適用範圍並指向本檔。
- 觸發來源：intent `260916-estimate-upload-rework` 的 intent-capture 審查 R-02、feasibility 的 `constraint-register.md` C-01 與 `raid-log.md` ISSUE-01／DEP-04、scope-definition Q4 定案 A（「現在就開」）。

## Context

C1 成本估算在 2026-08-19 的 practices-discovery 訪談中確立了一套架構：`cost_router` → `cost_service` → 純函式 `cost_calculator`，外加一個獨立的 `pricing_client` 作為外部計價 Port。同一輪訪談也確立了 `pricing_client` 只准對接公開免帳號的價目端點，禁用需要雲端帳號憑證的 Cost Explorer／Billing API。這五條規則寫進了 `project.md` 與 `team.md`，並各自帶 `affirmed 2026-08-19` 標記。

這套架構的前提是**系統自己去取價**：讀架構圖、對 SKU、打公開價目端點，或以 Playwright 自動操作官方 Calculator。

intent `260916-estimate-upload-rework` 把這個前提整個拿掉。intent-capture Q2 定案為「完全取代」：價格由使用者上傳官方估價表提供，系統不再向任何外部來源取價。feasibility Q5 定案為全數移除——`cost_router.py` 的 9 個端點、4 張資料表（`diagram_cost`、`diagram_cost_line`、`pricing_cache`、`cost_audit_event`）、兩支 Playwright runner 與 `pricing_client.py` 本身。

於是五條規則中有數條**失去了適用對象**：規則要求存在的 `pricing_client` 即將不存在。這不是可以靠解讀繞過的——規則明文仍在，且都是 `ALWAYS`／`NEVER` 等級。intent-capture 的 reviewer 判定為 Major（R-02），feasibility 把它登錄為阻擋 construction 的依賴（DEP-04）。

**本 ADR 是解除這個衝突唯一有效的形式。** 在 stage 產出或 RAID log 裡寫「需要一份 ADR」，對規則層本身沒有任何效力；`project.md` 的 `## Forbidden` 明文要求專案規則一律寫在 memory 層，而規則層的架構級變更依 `## Mandated` 必須開 ADR。

## Decision

### 1. `pricing_client` 的存在強制要求：**廢止**

> **本節已由 §8 部分撤回。** 不得單獨引用。

`project.md` 第 120 行要求「另獨立 `pricing_client`」。該子句**廢止**，理由是它所要求的元件在新架構下沒有職責——沒有任何外部計價端點需要被包裝。

`pricing_client.py` 連同其消費端（`sku_mapper.py`、`price_cache.py`、`pricing_azure.py`、`pricing_gcp.py`、`pricing_sdk.py`、`pricing_offer_parser.py`、`pricing_query_parser.py`、`pricing_units.py`、`pricing_urls.yaml`、`pricing_coverage.yaml`）一併退場。

### 2. 三層形狀：**保留，但重新定錨**

`cost_router` → `cost_service` → 純函式核心的三層形狀**繼續有效**，這條不因取價方式改變而失效。它的價值在於「純函式核心不讀 DB、不連外、不 raise `HTTPException`」這個結構前提——那是 ADR-0006 的 property-based testing hard constraint 能在核心起作用的唯一依據，與價格從哪來無關。

純函式層的**名稱與職責改變**：

| 原 | 新 | 職責 |
|---|---|---|
| `cost_calculator`（依 SKU 與時數計算金額） | 估價表解析器 | 把 AWS CSV／Azure XLSX／GCP CSV 解析成結構化品項 |

禁止事項原樣繼承到新的純函式層：**不得 import `httpx`、任何 DB session 型別，或 `HTTPException`**。解析器是純函式，因此 ADR-0006 的 PBT hard constraint 由 `cost_calculator` 原樣移轉到它身上，**不是豁免、也不是新增**。

同樣繼承的還有：禁止把 cost 邏輯寫進 `user_router.py` 或 `wa_rule_engine.py`。

### 3. 計價 API 禁令：**保留，且在新架構下自動成立**

> **本節已由 §8 部分改述。** 不得單獨引用。

`project.md` 第 79 行（禁用需憑證的 Cost Explorer／Billing／Cost Management 作為 C1 價目來源）與第 83 行（新計價呼叫必須走獨立 `pricing_client`）的**意圖**是防止本 repo 取得或要求雲端帳號憑證。該意圖**完全保留**。

第 79 行在新架構下**自動成立**且更強：系統不再呼叫任何計價 API，連公開免帳號的也不呼叫。改述為：**C1 的價目來源只有使用者上傳的官方估價表一種，不得新增任何自動取價路徑（不論該端點是否需要憑證）。**

第 83 行的「必須走獨立 `pricing_client`」子句隨 §1 廢止。其前半段——**不得在 n8n／PNG 呼叫點或任何其他位置用 `httpx` 直接打雲端 Pricing API**——保留，且因 §1 不再有例外出口，它成為無條件禁令。

### 4. `team.md` 第 196、198 行：同步限定

`team.md` 的兩條是 `project.md` 對應規則的展開版本，處置與 §1–§3 一致：三層形狀保留並改錨到解析器，`pricing_client` 子句廢止，計價 API 禁令保留並升格為無條件。

### 5. 不受本 ADR 影響、仍然有效的 C1 規則

逐項列出以免被誤讀為一併廢止：

| 規則 | 位置 | 狀態 |
|---|---|---|
| 第一個 C1 HTTP 端點須有 allow／deny 雙向 TestClient | `project.md` `## Mandated` | **有效**，且因舊端點全數移除、新端點是「第一個」，本條重新觸發 |
| 不得把 WA `COST-*` 啟發式 findings 當成已實作的成本計算能力 | `project.md` `## Forbidden` | **有效**，不受影響 |
| 不得把 RBAC 種子或權限頁的 C1 欄當成已有 cost router／Cost 頁 | `project.md` `## Forbidden` | **有效**，且退場後本條再次成為字面事實 |
| 不得把 Assessment 的雲端供應商下拉當成 pricing Manual Override | `project.md` `## Forbidden` | **有效**，Manual Override 概念雖退場，本條的防誤讀意圖不變 |
| ADR-0006 安全基線四面向、property-based testing | `project.md` `## Decided` | **有效**，PBT 落點由 `cost_calculator` 移轉至解析器 |
| schema 變更需同步 `schema_rbac.sql` 與 `DEPLOY.md` | `project.md` `## Mandated` | **有效**，4 張表移除與新表新增都觸發 |

### 8. 同日修訂：`pricing_client` 以「agent 查價工具」的身分復活，§1 與 §3 部分撤回

本節追加於 2026-09-16T07:20Z，即本 ADR 建立後約 25 分鐘，觸發來源為 approval-handoff 階段使用者提出「三朵雲想保留查詢官網 API 的功能」。

**§1 與 §3 的前提有誤。** §1 廢止 `pricing_client` 的理由是「沒有任何外部計價端點需要被包裝」；§3 把計價 API 禁令改述為「不得新增任何自動取價路徑」。兩者都建立在「新架構完全不需要對外取價」這個假設上，而該假設在同日被使用者推翻。

**撤回的範圍極小，必須精確界定。** 復活的不是舊的取價子系統，而是一個**給 agent 用的按需查價工具**：

| 面向 | §1／§3 原本的斷言 | §8 修訂後 |
|---|---|---|
| `pricing_client` 是否存在 | 廢止，無職責 | **存在**，職責為包裝公開價目端點供 agent 呼叫 |
| 呼叫時機 | 不呼叫 | agent 產生建議時**按需**呼叫，非例行、非逐列 |
| 呼叫者 | 無 | 只有 agent。系統本身不主動取價 |
| 價目來源的權威性 | 上傳估價表為唯一來源 | **不變**：上傳估價表仍是唯一的估價來源 |
| 查得的價格如何使用 | N/A | **只寫進建議文字**，不得覆蓋、不得改寫明細表的任何數值 |
| 憑證 | N/A | 只准公開免帳號端點。走 IAM 的 boto3 Pricing Query API **仍然禁止** |

**§1 撤回的部分**：「`pricing_client` 的存在強制要求廢止」撤回。`project.md` 第 120 行要求的獨立 `pricing_client` **恢復有效**。

§1 列出的退場清單中，`pricing_client.py` 本身**留下**；其餘消費端（`sku_mapper.py`、`price_cache.py`、`pricing_azure.py`、`pricing_gcp.py`、`pricing_sdk.py`、`pricing_offer_parser.py`、`pricing_query_parser.py`、`pricing_units.py`、`pricing_urls.yaml`、`pricing_coverage.yaml`）的去留由 code-generation 依「agent 查價工具實際需要什麼」判定，**不預先承諾全留或全刪**。可確定刪除的是 `pricing_sdk.py`：它是 boto3 IAM 路徑，本節明文仍禁。

**§3 撤回的部分**：「不得新增任何自動取價路徑」改述為——

> **不得以自動取價產生估價。** 估價一律來自使用者上傳的官方估價表。agent 於產生建議時得呼叫公開免帳號的價目端點確認現價，所得價格只得寫入建議文字，不得回寫明細表。

§3 的其餘部分不變：`httpx` 不得在 n8n／PNG 呼叫點或其他位置直打雲端 Pricing API，一律走 `pricing_client`；需要雲端帳號憑證的端點一律禁止。

**§2 不受影響。** 三層形狀與純函式解析器的安排與取價無關，原樣有效。`pricing_client` 作為獨立 Port 的定位，正是它不會污染純函式層的原因。

**本節不恢復的東西**（逐項列出，避免被讀成整個 §1 撤回）：`pricing_cache` 資料表仍在退場清單；逐列自動核對**不做**；完整 SKU 對應**不做**；`cost_router.py` 的 9 個端點仍全數移除。

**代價**：agent 按需查價是 LLM 自行決定要不要查，同一份估價表跑兩次可能查不同品項。因此本節**不構成** approval-handoff AH-1 所要求的機械檢查——該義務仍然懸著，由另一層不需 SKU 對應的確定性檢查（總額對帳、幣別一致性、數量合理範圍）承擔。兩者是互補而非替代，不得在下游被合併處理。

## Consequences

**正面**：construction 的阻擋解除；規則層與即將落地的架構一致；PBT hard constraint 有明確的新落點，不會在 `cost_calculator` 消失時一併蒸發。

**負面**：五條規則的 `affirmed 2026-08-19` 紀錄在生效不到一個月後即被部分廢止。這不代表當時的訪談做錯——當時的架構前提是真的，是前提本身被換掉了。但它意味著 memory 層的 `affirmed` 標記不應被讀成「已驗證為長期正確」。

**殘餘風險**：§2 的「三層形狀保留但純函式層改名」是本 ADR 唯一有解讀空間的部分。若下游把「解析器」實作成會讀 DB 或發 HTTP 的東西，三層形狀在字面上仍然成立，但 PBT 約束會失去落點而無人察覺。可執行檢查：解析器模組內 `import httpx`、DB session 型別、`HTTPException` 三者的 grep 結果必須為零。

## Alternatives Considered

**A. 不開 ADR，直接修改 `project.md` 與 `team.md` 的規則文字。** 否決：`project.md` `## Mandated` 明文要求架構級決策開 ADR 於 `<record>/inception/decisions/`。且直接改文字會讓「為什麼改」只存在於 git log，下一個讀規則的人看不到 2026-08-19 的訪談前提已經不成立。

**B. 保留 `pricing_client` 作為空殼以維持規則字面成立。** 否決：死碼在文件上長得像已實作的能力，這正是 `project.md` 另外四條 `NEVER` 規則（WA findings、Assessment 下拉、RBAC 種子）反覆在防的形狀。

**C. 拖到 construction 開始前再處理。** 否決：scope-definition Q4 已定案 A（現在就開）。拖延的成本是單向上升的——inception 的 requirements-analysis、domain-design、contract-design 都會在一套字面失效的規則下產出，屆時回頭修正的傳播面遠大於現在。

**D. 另開獨立 intent 專門收斂規則層。** 否決：規則衝突是本 intent 的產物，不是獨立的技術債；拆出去會讓本 intent 的 construction 依賴另一個 intent 的完成時點。

## 對應的規則層編輯

本 ADR 生效時，下列五處就地加註限定，**原文保留不刪**。下列文字已計入 §8 的修訂，與 §1／§3 首版不同：

1. `project.md:79` — 追加「本條於 ADR-0017 §3＋§8 改述為『估價一律來自使用者上傳的官方估價表；agent 得查公開免帳號端點確認現價，所得價格僅供建議文字使用』」
2. `project.md:83` — 追加「`httpx` 不得在任何位置直打雲端 Pricing API，一律走 `pricing_client`；`pricing_client` 於 §8 恢復效力」
3. `project.md:120` — 追加「三層形狀與純函式禁令保留，純函式層由 `cost_calculator` 改錨至估價表解析器（§2）；`pricing_client` 於 §8 恢復為 agent 按需查價工具」
4. `team.md:196` — 同第 3 項
5. `team.md:198` — 同第 1、2 項

## Assumptions & Open Questions

- [assumption] §8 假設公開免帳號端點足以支撐 agent 的查價需求。AWS Bulk Price List 與 Azure Retail Prices 確為公開；GCP Cloud Billing Catalog 需 `GCP_BILLING_API_KEY`——該金鑰是 API key 而非帳號憑證，本 ADR 判定其不觸犯「免帳號」要求，但此判定未經法務或安全審查。
- [assumption] §8 假設「只寫進建議文字、不回寫明細」這條界線在實作上守得住。若下游為了呈現方便而在明細表加上查得的價格欄位，界線即被跨越，須回頭修訂本節。
- [assumption] §2 假設估價表解析器確實會是純函式。若 domain-design 決定解析過程需要查詢資料庫（例如比對既有的 SKU 對照表），這個假設不成立，PBT 落點需要重新指定。
- [open] 本 ADR 不處理 `deploy/render-env.sh` 的 `AWS_SECRET_ACCESS_KEY` repo contract 違規（feasibility ISSUE-03）。該項與 C1 架構無關，是獨立的既有問題，仍阻擋 CI 綠燈。
- [open] `backend/cost/` 下 30 個檔案中，退場清單以 feasibility 的盤點為準。若 code-generation 階段發現其他模組對這些檔案有隱性依賴，退場範圍需重新確認（ASSUM-04）。
