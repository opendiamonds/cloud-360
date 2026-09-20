# Unit of Work — Story Map

> 將 `stories.md` 的七則 C1 對到 unit。跨 unit 故事列出主責與協作。  
> 單元**內部**故事序是驗收依賴（C1-1 支撐 C1-2 等），不是 2.8 的 Bolt 順序。  
> 亦對齊 `requirements.md` FR 與 `components.md` 權限列。

## Story → Unit

| Story | 標題 | 段 | AC 數 | 主責 unit | 協作 unit |
|---|---|---|---|---|---|
| C1-1 | 進入成本頁並看到對到圖的資源列 | 第一段 | 13 | `cost-ui` | `cost-api`（擷取／快照）、`cost-schema-rbac`（列／區域表與 `C1.view` 種子） |
| C1-2 | 官方價、每月總額與圓餅 | 第一段 | 5 | `cost-api` | `cost-calculator`（總額／圓餅）、`cost-ui`（圓餅 SVG 與定價假設） |
| C1-3 | 產圖後一鍵查看預估成本 | 第一段 | 2 | `cost-ui` | （Workspace 成功卡為既有 A1 掛點，非本 intent unit） |
| C1-4 | 架構師每日時數與估價區域 | 第一段 | 9 | `cost-ui` | `cost-api`（PUT hours／region）、`cost-calculator`（就地重算公式）、`cost-schema-rbac`（`C1h`／`C1r`） |
| C1-5 | FinOps SKU／小時價覆寫與稽核 | 第一段 | 9 | `cost-api` | `cost-ui`（就地表格）、`cost-calculator`（`O × h × 30`）、`cost-schema-rbac`（稽核表、`C1o`） |
| C1-6 | 每圖每月預算 | 第二段 | 4 | `cost-budget-banner` | `cost-api`（加掛 PUT budget）、`cost-schema-rbac`（`monthly_budget`、`C1b`）、`cost-ui`（預算欄掛在 CostPage） |
| C1-7 | 已超支＋進產品橫幅 | 第二段 | 5 | `cost-budget-banner` | `cost-calculator`（`is_overspent`）、`cost-api`（`GET /banner`）、`cost-ui`（頁上旗標掛點） |

AC 合計：13+5+2+9+9+4+5 = **47**（與 `stories.md` 標題列逐條計數一致）。

對齊註記（非本站新定案）：上游 C1-6 的 AC 標題為 6.1／6.2／6.3／6.5，沒有 6.4 列；Round 1 摘要只記錄刪 AC-4.4／AC-5.6（舊編號，Given 在第二段為假）。本站不回改 `stories.md`。

## Unit → Stories（反向）

| Unit | 主責 | 協作出現 | 一句話 |
|---|---|---|---|
| `cost-schema-rbac` | （無單一產品故事只活在 SQL） | C1-1、C1-4、C1-5、C1-6 | 四表＋只補缺失種子；每個會寫狀態或授權的故事都碰它 |
| `cost-calculator` | （公式無獨立使用者故事） | C1-2、C1-4、C1-5、C1-7 | 純函式；PBT 掛 C1-2／C1-1 DoD 所述具名性質 |
| `cost-api` | C1-2、C1-5 | C1-1、C1-4、C1-6、C1-7 | 第一段 HTTP 與編排；第二段只加掛、不另起 process |
| `cost-ui` | C1-1、C1-3、C1-4 | C1-2、C1-5、C1-6、C1-7 | `/cost`、Sidebar、CTA；第二段只加欄位與旗標 |
| `cost-budget-banner` | C1-6、C1-7 | — | 預算 API＋橫幅＋「已超支」 |

`cost-schema-rbac` 與 `cost-calculator` 沒有「只屬於自己的」使用者故事，但每個都有協作覆蓋，滿足「every unit has stories」。它們的完成判準是契約／PBT，不是獨立畫面（切分理由見 `units-generation:c6`）。

## 跨 unit 故事

| Story | 為什麼不能單 unit | 整合點 |
|---|---|---|
| C1-1 | 列來自 XML 擷取（api）＋表對齊（schema）＋Sidebar／空狀態（ui） | `GET /diagrams/{id}` 的 `lines[]` |
| C1-2 | 總額在 calculator；快取／pricing_client 在 api；圓餅在 ui | snapshot `total`／`pie` |
| C1-4 | 控件在 ui；422 在 api；公式在 calculator | `PUT .../hours`、`PUT .../region` |
| C1-5 | 覆寫 HTTP＋稽核在 api；表格在 ui | `PUT .../sku`、`PUT .../override`、`GET .../audit` |
| C1-6 | 預算欄在 ui 殼上；寫入在第二段 api；欄位在 schema | `PUT .../budget` |
| C1-7 | 旗標在 CostPage；橫幅在 Layout；判定在 calculator | `GET /banner`、`overspent` |

C1-3 不跨本 intent 的後端 unit：只要求成功卡 CTA 與無 id 存檔閘（ui）。

## 單元內故事序（驗收依賴，非 Bolt）

對齊 `stories.md` 建置依賴。僅約束**同一 unit 內**先後驗收，避免 AC 的 Given 為假。

| Unit | 單元內序 |
|---|---|
| `cost-schema-rbac` | 表與 `C1.view` 種子 → 再補 `C1h`／`C1r`／`C1o`／`C1b` 缺失列（同一 ensure 函式可一次插入，序只表示測試可先 assert 表再 assert 種子） |
| `cost-calculator` | `total_priced`／`pie_buckets`（C1-2）與 `line_subtotal`（C1-4／C1-5）可同測；`is_overspent`（C1-7）與其餘純函式無呼叫環 |
| `cost-api` | 快照讀取（C1-1／C1-2）支撐 hours／region（C1-4）與覆寫／稽核（C1-5）。第二段路由不在本 unit 第一段註冊 |
| `cost-ui` | C1-1 入口與列 → C1-2 總額／圓餅與 C1-4 時數／區域與 C1-3 CTA 都假設頁已存在；C1-5 表格假設列已在。C1-1 的 AC-1.16 在本 unit 驗「第二段 DOM 不存在」 |
| `cost-budget-banner` | C1-6 預算值支撐 C1-7 超支判定（`stories.md`：C1-6 → C1-7） |

## 覆蓋檢查

- [x] C1-1～C1-7 皆已指派主責
- [x] 本檔 AC 數加總 47，與 `stories.md` 的 `**AC-` 標題列數相同
- [x] 五個 unit 皆至少以主責或協作出現
- [x] C2／C3 本輪無故事、無 unit（Won't Have）
- [x] 第一段故事（C1-1～C1-5）不把 `cost-budget-banner` 當主責
- [x] 第二段故事（C1-6、C1-7）主責皆為 `cost-budget-banner`
