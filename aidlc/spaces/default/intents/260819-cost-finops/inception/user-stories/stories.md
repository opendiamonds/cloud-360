# User Stories — C1 專案 TCO 與流量預算預測（本輪不含流量／egress）

<!-- Stage: user-stories（Inception 2.4，mob）· 編號沿用 baseline **C1**。
     Q1–Q4=A。Round 1 已折入 design／developer／quality 事實類 OBJECT。
     判斷題 Q5=A（C1-1 拆三則）、Q6=A（時數 0–24）。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）
- **business-overview**／**component-inventory**（`aidlc/spaces/default/codekb/cloud/`）
- **team-practices**（`../practices-discovery/team-practices.md`）
- **personas**（`./personas.md`）
- **baseline-C**（`260802-default/.../stories.md` #### C1）
- **contributions/**：Round 1 三份盲審

## Round 1 整合摘要

| 修正 | 依據 |
|---|---|
| h1 為「預估成本」，總額是視覺置頂不是 h1 | design V-7／OBJECT 1 |
| 第一段補切圖、Sidebar 預選、載入／錯誤、全未定價、CTA 存檔閘、鍵盤／窄視窗 | design OBJECT 2–7 |
| 第一段負向：無預算欄、無「已超支」、無橫幅；覆寫子句移出 C1-1 | quality 缺口 A／C |
| 刪 AC-4.4／AC-5.6（Given 在第二段為假） | quality 缺口 B |
| SPA Forbidden 與 API 403 分層；Playwright 斷言寫死 | developer／quality |
| 擷取為新 overlay，禁止 `parse_diagram_summary`／`wa_rule_engine`／`user_router` | developer OBJECT |
| schema／OpenAPI／DEPLOY／ensure 列入各段 DoD | developer OBJECT |
| 覆寫定錨為小時 list price，小計 `O × h × 30` | developer／quality（現 AC-5.3） |
| 具名 PBT 掛 C1-2／C1-1；403 allow/deny 成對 | quality |
| 橫幅含圖名、總額、預算；未設預算不超支 | design |
| 產品四種變更權仍為語意；view／edit／review 映射 OQ-1；改種子須 A 規則 | developer OBJECT 4 |
| Q5=A：原 C1-1 拆為 C1-1 入口擷取、C1-2 官方價圓餅、C1-3 產圖 CTA | 人類判斷 |
| Q6=A：每日時數 0–24（含），非法不送出 | 人類判斷 |

## 與 baseline C1 的差異（刻意覆寫）

| baseline C1 | 本輪 |
|---|---|
| 僅 David、Hannah | 含 Alex |
| 預設 8 小時、David 改時數 | 預設 24；僅 Alex 改時數／區域 |
| 改時數標 Manual Override | 時數 ≠ 單價覆寫 |
| 流量模型重置 | 無 egress／流量模型 |
| Billing Alarm／inbox | 「已超支」＋進產品橫幅 |
| 灰色「定價無法獲取」 | 未定價列名；失敗另標「官方價取得失敗」 |

## 優先序與依賴

七則皆 **Must Have**。C1-1～C1-5 第一段可單獨上線。C1-6／C1-7 第二段。

```
建置依賴：
  C1-1 --> C1-2
  C1-1 --> C1-3
  C1-1 --> C1-4
  C1-2 --> C1-5
  C1-2 --> C1-6 --> C1-7
```

<!-- Text fallback: 先有入口與列擷取（C1-1），才能查官方價與總額（C1-2）以及產圖 CTA 落地（C1-3）。時數（C1-4）建在列上；覆寫（C1-5）與預算（C1-6）建在總額上；超支（C1-7）建在預算上。 -->

**INVEST Independent**：總額依賴真實，完全 Independent 不可得。

**Won't Have**：C2、C3、egress 列、核准流、inbox、Cost Explorer／客戶帳單、WA `COST-*` 當 TCO。

**授權契約**：下列 403／allow 是產品語意。HEAD 的 C1 `view`／`edit`／`review` 種子不足以表達四種變更；映射為 OQ-1。改種子時須 allow／deny 雙向測試，並讓既有 DB 列生效（`force=False` 會 no-op）。

---

## C1-1 進入成本頁並看到對到圖的資源列

> **As a** Alex（David／Hannah 具 C1 view 可看同一列集合），
> **I want** 從 Sidebar 打開成本頁、選圖，並看到對到圖上節點的資源列（含未定價佔位），
> **so that** 我知道「這張圖有哪些東西要估價」，即使官方價還沒回來。

**優先序**：Must Have（第一段）
**建置依賴**：無
**涵蓋**：FR-1.1～FR-1.3、FR-1.5、FR-5.1、FR-5.3、FR-5.4、FR-4.1 提示、FR-7.1 第一段列／區域欄、FR-8.1、NFR-1／NFR-2

### 驗收標準

**AC-1.1 Sidebar 入口（UI）**
- **Given** Alex 具 C1 view
- **When** 他檢視 Sidebar
- **Then** 「架構」與「系統管理」之間出現「成本」，其下有「預估成本」（畫面標籤；FR-5.1 所稱 Admin 區塊）
- **And** 無 C1 view 的帳號看不到「成本」組

**AC-1.1b 無 C1 view 的頁與 API**
- **Given** 帳號無 C1 view
- **When** 他開啟成本頁路由
- **Then** 看到既有 Forbidden 頁（`/403`），不是空白主區、也不是被 `DefaultRedirect` 送到 Workspace
- **And** 呼叫讀取成本 API 得到 HTTP 403

**AC-1.3 空狀態**
- **Given** 沒有任何架構圖，或有圖但尚未選圖
- **When** 進入成本畫面
- **Then** 總額數字節點不存在（金額 test-id 0 命中）；空狀態可見；若有圖則提供圖下拉與前往架構圖生成

**AC-1.4 可估價列**
- **Given** 所選圖 XML 含可估價節點：`mxCell` 且 `edge` 不為 1、去掉 HTML 後 label 非空、style 不含 `group`、`swimlane`、`container=1`
- **When** 成本畫面完成載入
- **Then** 每一列資源名等於該節點去掉 HTML 後的 label；列數等於可估價節點數
- **And** 連線、無文字裝飾、VPC／群組容器不出現在列上
- **And** 擷取不得呼叫 `parse_diagram_summary` 當作列集合

**AC-1.5 跟圖走（第一段不含覆寫）**
- **Given** 成本頁已對圖顯示 N 列
- **When** Alex 新增一個可估價節點並再打開成本頁
- **Then** 列數為 N+1，新列每日時數為 24
- **And** 刪除節點後該 mxCell `id` 的列消失
- **And** 只改 label 時同一 `id` 的每日時數仍在，資源名改為新 label

**AC-1.6 未定價佔位**
- **Given** 若干列對不到唯一公開 SKU 或所屬雲無公開免帳號價目
- **When** 畫面顯示
- **Then** 那些列不顯示官方單價；出現「N 項尚未定價」，N 等於未定價列數

**AC-1.8 估價區域未填（UI）**
- **Given** 該圖尚未設定估價區域
- **When** Alex 檢視成本頁
- **Then** 畫面提示區域必填；不顯示捏造的官方單價

**AC-1.11 第一段切圖**
- **Given** Alex 可估價的圖有兩張以上，成本頁顯示圖 A
- **When** 他用頁首「圖」下拉改選圖 B
- **Then** 列集合改綁圖 B，不再出現圖 A 的列

**AC-1.12 Sidebar 預選上次**
- **Given** 同一瀏覽器先前在成本頁選過圖 A
- **When** 從 Sidebar「成本 → 預估成本」進入
- **Then** 預選圖 A；若圖已不可見則走 AC-1.3

**AC-1.13 載入與頁級錯誤**
- **Given** 已選圖，列資料尚未到達或請求失敗
- **When** 成本頁渲染
- **Then** 總額數字節點不存在；載入中有可見文字
- **And** 失敗時有文字說明與可啟動的重試，主區不是空白

**AC-1.14 零可估價節點**
- **Given** 所選圖沒有可估價節點
- **When** 畫面完成載入
- **Then** 說明尚無可估價列；不把 `USD 0` 呈現成已完成的對外估價

**AC-1.15 鍵盤與窄視窗**
- **Given** 具 C1 view 的使用者只使用鍵盤
- **When** 操作圖下拉、估價區域
- **Then** 都能聚焦並啟動，焦點可見
- **And** 對比 ≥ 4.5:1 為人工驗收
- **And** 窄視窗可捲動讀完列與空狀態，不斷開圖下拉

**AC-1.16 第一段不含第二段 UI**
- **Given** 第一段建置已部署（C1-6／C1-7 未交付）
- **When** 開啟成本頁與任一受保護頁
- **Then** 不出現可編輯預算欄、文字「已超支」、進產品超支橫幅（test-id 0 命中）

### Definition of Done

- 新模組起點：`cost_router` → `cost_service`；擷取 overlay 為新程式，禁止寫進 `user_router.py`／`wa_rule_engine.py`；列集合不得等於 `parse_diagram_summary` 的 nodes
- 新表／欄：同步 `schema_rbac.sql`、`DEPLOY.md`、`database.py` ensure
- `openapi.json` 與 `frontend/src/types/api.d.ts` 無 drift
- TestClient：無權讀取 403；有權讀取列集合 2xx（總額可為尚未定價狀態）
- Playwright：Sidebar「成本→預估成本」；已選圖有資源列表頭與至少一列資源名；無圖時空狀態可見且總額節點 0 命中；無 C1 view 無「成本」組；受保護頁「已超支」與橫幅 0 命中
- 未設區域時攔截官方價 URL 且請求次數為 0

---

## C1-2 看到官方價、每月總額與圓餅

> **As a** Alex，
> **I want** 在已選圖且已填估價區域後看到 USD 總額與四類圓餅，
> **so that** 我能對外說明這張圖一個月大概多少錢。

**優先序**：Must Have（第一段）
**建置依賴**：C1-1
**涵蓋**：FR-2.1／FR-2.2／FR-2.5、FR-3.1／FR-3.4～FR-3.6、FR-7.1 第一段總額、FR-7.2、NFR-4

### 驗收標準

**AC-2.1 有權讀取含總額**
- **Given** Alex 具 C1 view、已選圖、已設區域
- **When** 呼叫讀取成本 API
- **Then** HTTP 2xx，body 含圖 id、列集合、已定價總額（尚無已定價列時為明確狀態，不是欄位缺失）

**AC-2.2 總額、圓餅、heading**
- **Given** 至少一列已定價
- **When** 畫面完成載入
- **Then** 總額等於已定價列小計之和
- **And** 加入或移除一筆未定價列後總額不變
- **And** 圓餅四類 compute／database／network／other，另附文字清單；四類已定價金額之和等於總額
- **And** 視覺順序為每月總額置頂 → 圓餅 → 資源列；heading 為 h1「預估成本」、h2「圓餅拆解」、h2「資源列」；總額數字不是 h1

**AC-2.3 定價假設**
- **Given** 已有至少一筆官方價
- **When** Alex 檢視成本頁
- **Then** 可見估價區域、USD、公式摘要（小時價 × 每日時數 × 30）、官方價來源時間（ISO-8601 UTC）
- **And** 可見本輪各雲是「走官方價」或「全 Manual Override」

**AC-2.4 第二人同一總額**
- **Given** David 具 C1 view
- **When** 他開啟 Alex 同一張圖
- **Then** 總額與已定價／未定價狀態與 Alex 一致

**AC-2.5 全未定價**
- **Given** 所有列皆未定價
- **When** 畫面完成載入
- **Then** 不把 `USD 0` 呈現成已完成的對外估價；仍顯示「N 項尚未定價」

### Definition of Done

- `pricing_client`＋純函式 `cost_calculator`（無 httpx／DB／HTTPException）；禁止寫進 `user_router.py`／`wa_rule_engine.py`
- PBT：`prop_total_is_sum_of_priced`、`prop_unpriced_excluded`
- TestClient 有權 2xx 含總額欄位；無權 403
- Playwright：已選圖且有已定價列時出現 USD 總額數字與圓餅文字清單
- OpenAPI／schema／DEPLOY 若本故事引入價目快取欄：同步
- 已快取、50 列內：已認證請求至總額節點 ≤ 5 秒（NFR-4）
- 全 Manual Override 雲（無公開免帳號端點）的列：官方價 HTTP stub 呼叫次數為 0（FR-2.2）

---

## C1-3 產圖後一鍵查看預估成本

> **As a** Alex，
> **I want** 在產圖成功卡點「查看預估成本」，
> **so that** 不必自己去 Sidebar 找剛產的那張圖。

**優先序**：Must Have（第一段）
**建置依賴**：C1-1
**涵蓋**：FR-5.2

### 驗收標準

**AC-3.1 有 id 時預選**
- **Given** 成功 overlay 可見且已有 `currentDiagramId`
- **When** Alex 點「查看預估成本」
- **Then** 進入成本畫面且預選該圖

**AC-3.2 無 id 存檔閘**
- **Given** overlay 尚無已存 id
- **When** Alex 尋找「查看預估成本」
- **Then** 該動作不可把使用者送進無處可預選的成本頁（控件停用，或先走既有存檔路徑再進入且預選新圖）

### Definition of Done

- Playwright：有 `currentDiagramId` 的成功卡可見「查看預估成本」，點擊後成本頁圖下拉值等於該 id
- 與既有成功卡三顆 CTA 並列，不取代它們

---

## C1-4 架構師用每日時數重算每月總額

> **As a** Alex，
> **I want** 在每一列就地改「每日時數」並立刻看到該列小計與總額重算，
> **so that** 我能用實際開機假設說明月費。

**優先序**：Must Have（第一段）
**建置依賴**：C1-1
**驗收依賴**：C1-2（就地重算總額）
**涵蓋**：FR-3.2、FR-3.3、FR-4.1、FR-7.1 第一段、FR-8.1、Q6

### 驗收標準

**AC-4.1 預設 24**
- **Given** 一個剛擷取的可估價列
- **When** 列第一次出現
- **Then** 每日時數為 24；無頁面級時數控件
- **And** 欄的可見名稱為「每日時數」

**AC-4.2 公式（example 僅 smoke）**
- **Given** 一列小時 list price 為 1、每日時數為 24
- **When** 計算月費
- **Then** 小計為 720
- **And** 僅月價 730 的 SKU，小時價為 `730 / 730`（即 1），時數 24 時小計為 720
- **And** 另備 h=0 與 h=8 的 example：小時價 1 時小計分別為 0 與 240
- **And** 小數位容差於 application-design 凍結前，PBT 用分數或固定小數位比較（見 DoD）

**AC-4.3 時數 deny**
- **Given** David 或 Hannah 已開啟成本頁
- **When** 他們嘗試改時數
- **Then** 時數欄不可編輯；該角色呼叫改時數 API 得到 HTTP 403

**AC-4.3b 時數 allow**
- **Given** Alex 具產品語意上的改時數權
- **When** 他將某列時數改為 8
- **Then** API 2xx，讀回該列時數為 8

**AC-4.4 區域 deny／allow**
- **Given** 非架構師
- **When** 呼叫設定／修改區域 API
- **Then** HTTP 403
- **And** Alex `PUT` 區域碼後 2xx，讀回 body 的區域碼等於請求值

**AC-4.5 持久化**
- **Given** Alex 將某列時數改為 8、區域設為 `ap-northeast-1`
- **When** 換瀏覽器以同一帳號再開該圖
- **Then** 時數為 8、區域為 `ap-northeast-1`

**AC-4.6 就地重算**
- **Given** 已定價列時數 24，小計與總額為當前公式值
- **When** Alex 改為 8 且未離開成本頁
- **Then** 該列小計與頁面總額改為新公式結果（不必整頁重載）
- **And** 總額變更能被輔助技術得知（`aria-live="polite"` 或同等）

**AC-4.7 估價區域控件**
- **Given** 成本頁已選圖
- **When** Alex 檢視定價假設區
- **Then** 估價區域有可見標籤且可編輯；未填時主區提示必填
- **And** David／Hannah 看見同一區域碼，控件不可編輯

**AC-4.8 每日時數區間 0–24（含）**
- **Given** Alex 正在編輯一列「每日時數」
- **When** 他輸入整數 0 或 24 並送出
- **Then** API 2xx，讀回該列時數等於輸入值
- **And** 輸入空白、非數字、非整數、小於 0 或大於 24 時不送出請求；列旁有可見文字錯誤；先前已存的合法時數不變

### Definition of Done

- TestClient：Alex 改時數／區域 2xx 欄位集；David／Hannah 403；時數 0 與 24 可寫入；-1／25 得到 4xx 且列值不變
- Playwright：改時數後該列小計與頁面總額數字變更；非法時數有文字錯誤且總額不變
- PBT：`prop_hours_formula`（`小計 = p * h * 30`）、`prop_monthly_sku_hourly`（小時價 = `M / 730`）；`h` 的 Hypothesis domain 為整數 0–24（含）
- schema／OpenAPI／DEPLOY 若本故事引入時數／區域欄：同步

---

## C1-5 缺價或失敗時由 FinOps 補上可報價狀態

> **As a** David，
> **I want** 為未定價列指定公開 SKU，或在官方價失敗時覆寫**小時 list price**並標 Manual Override，
> **so that** 畫面可報價，而不連 Cost Explorer、也不把缺價當成 0。

**優先序**：Must Have（第一段）
**建置依賴**：C1-2
**涵蓋**：FR-1.4、FR-2.3、FR-2.4、FR-2.5、FR-8.2、FR-8.3、NFR-3

### 驗收標準

**AC-5.1 官方價（可布置 stub）**
- **Given** 對照表唯一命中，定價 stub 回小時價 `p=1.25` 與來源時間 `T`
- **When** 成本頁載入該列
- **Then** 該列單價等於 `1.25`，來源時間等於 `T`（ISO-8601 UTC）

**AC-5.2 官方價失敗覆寫前**
- **Given** 已對到 SKU 但 stub 失敗或該 SKU 缺價，David 尚未覆寫
- **When** 畫面顯示
- **Then** 該列不計入總額，計入「N 項尚未定價」，並顯示「官方價取得失敗」（與從未對到 SKU 可區分，不只靠顏色）

**AC-5.3 覆寫後（量綱：小時價）**
- **Given** 失敗列，每日時數 `h`
- **When** David 覆寫小時 list price 為 `O`
- **Then** 小計 = `O × h × 30`（與 C1-4 同一公式）
- **And** 列上可見「Manual Override」，不再顯示「官方價取得失敗」

**AC-5.4a 指定 SKU 後 stub 回價**
- **Given** 未定價列，David 指定唯一 SKU，stub 回 `p`
- **When** 查價完成
- **Then** 單價等於 `p`（同 AC-5.1）

**AC-5.4b 指定 SKU 後 stub 失敗**
- **Given** 未定價列，David 指定唯一 SKU，stub 失敗
- **When** 畫面顯示
- **Then** 走 AC-5.2 的失敗文字

**AC-5.5 deny／allow**
- **Given** Alex 或 Hannah
- **When** 嘗試覆寫或指定 SKU
- **Then** 控件不可編輯；API HTTP 403
- **And** David 覆寫後 2xx，讀回該列覆寫小時價等於請求值

**AC-5.7 稽核**
- **Given** David 將某列覆寫小時價從 A 改為 B
- **When** 變更完成
- **Then** 稽核查詢（路徑於 OpenAPI 定案後填入；未定案前人工查 DB 列）回傳操作者、時間、圖 id、舊值、新值

**AC-5.8 重擷取不蓋覆寫**
- **Given** 某 mxCell `id` 已有 FinOps SKU 或小時價覆寫
- **When** 依目前 XML 重擷取
- **Then** 該 `id` 的 SKU／覆寫不被自動對照蓋掉

**AC-5.9 第二人可見覆寫**
- **Given** David 已覆寫某列
- **When** Alex 以 C1 view 開啟同一圖
- **Then** 他看得到覆寫後的單價顯示與 Manual Override 文字，但不能編輯

### Definition of Done

- PBT：`prop_override_precedes_list`、`prop_unpriced_excluded`（失敗覆寫前）
- TestClient：David 覆寫 2xx 欄位集；Alex／Hannah 403
- 靜態：repo／env 範本不得出現 Cost Explorer／Billing／Cost Management 憑證路徑（Forbidden，非使用者 AC）
- schema 稽核表或可查詢介面＋ OpenAPI／DEPLOY 同步

---

## C1-6 為每張架構圖設定每月預算

> **As a** David 或 Hannah，
> **I want** 為單張架構圖設定每月 USD 預算上限，
> **so that** 超支判定綁在這張圖。

**優先序**：Must Have（第二段）
**建置依賴**：C1-2
**涵蓋**：FR-6.1、FR-6.2、FR-7.1 第二段、FR-8.3

### 驗收標準

**AC-6.1 每圖一個預算值**
- **Given** 圖 A、圖 B 皆可寫預算
- **When** David 將圖 A 預算設為 100、圖 B 設為 1000
- **Then** 讀回圖 A 預算為 100、圖 B 為 1000（兩值獨立）

**AC-6.2 deny／allow**
- **Given** Alex
- **When** 呼叫改預算 API
- **Then** HTTP 403；預算控件不可編輯
- **And** David 或 Hannah 寫入後 2xx，讀回值等於寫入值

**AC-6.3 稽核**
- **Given** Hannah 將圖 A 預算從 100 改為 300
- **When** 變更完成
- **Then** 稽核查詢（同 AC-5.7 介面約定）含操作者、時間、圖 id、舊值、新值

**AC-6.5 尚未設定預算**
- **Given** 第二段已上線，所選圖沒有預算值
- **When** 檢視總額
- **Then** 不顯示「已超支」；預算欄為空且有權角色可填
- **And** 進產品橫幅不因「無預算」而出現

### Definition of Done

- TestClient：David／Hannah 改預算 2xx 欄位集；Alex 403；若改 C1 種子則 allow／deny 雙向＋既有環境列生效
- Playwright：有權角色看得見預算欄並能提交；Alex 看不見可編輯預算
- schema／OpenAPI／DEPLOY 同步
- 鍵盤可達預算控件（NFR-1；與 C1-1 AC-1.15 同類）

---

## C1-7 超支時在成本畫面與進產品時都看得到

> **As a** Alex、David 或 Hannah，
> **I want** 總額超過該圖預算時在成本頁看到「已超支」，且每次進入產品都看到不能永久關掉的橫幅，
> **so that** 沒有人能靠關閉通知而漏接。

**優先序**：Must Have（第二段）
**建置依賴**：C1-6
**驗收依賴**：C1-1
**涵蓋**：FR-6.3～FR-6.7、FR-5.4、requirements Q5、NFR-1

### 驗收標準

**AC-7.1 成本頁標示**
- **Given** 所選圖總額 > 預算
- **When** 成本頁顯示總額
- **Then** 總額旁有文字「已超支」且總額變色（不只靠顏色）

**AC-7.2 未超支**
- **Given** 總額 ≤ 預算（含相等）
- **When** 檢視總額
- **Then** 不顯示「已超支」

**AC-7.3 橫幅每次進入**
- **Given** 使用者可見的圖仍有至少一張超支
- **When** 登入後進入任一受保護頁（含關閉瀏覽器再登入）
- **Then** 看到一條橫幅，文字含至少一張超支圖名、該圖每月總額與預算（USD）、可鍵盤啟動的「前往成本畫面」
- **And** 沒有「永遠不要再顯示」

**AC-7.4 多圖一條橫幅**
- **Given** 兩張以上可見圖超支
- **When** 橫幅出現
- **Then** 仍只有一條：顯示超支圖數量，並點名至少一張
- **And** 「前往成本畫面」預選的圖 id 屬於超支集合；可用頁首下拉切到其他圖

**AC-7.5 無 inbox（人工／靜態）**
- **Given** 本輪產品
- **When** 依 Sidebar 與路由表盤點
- **Then** 無通知中心、未讀數、通知歷史入口（靜態盤點，非 e2e 窮舉）

### Definition of Done

- Playwright：成本頁「已超支」文字；登入後受保護頁橫幅存在；無「永遠不要再顯示」
- 超支狀態伺服器持久化（schema／DEPLOY）
- 橫幅「前往」可鍵盤啟動

---

## 需求追溯

| Scope / FR | 故事 |
|---|---|
| (e)(b) 入口、空狀態、擷取、切圖、載入錯誤 | C1-1 |
| (a)(d) 官方價、總額、圓餅、定價假設 | C1-2 |
| (e) 產圖 CTA | C1-3 |
| (d) 時數公式、估價區域控件 | C1-4 |
| (a)(c) 單價、覆寫、稽核 | C1-5 |
| (f) 每圖預算 | C1-6 |
| (g) 超支＋橫幅 | C1-7 |
| (h) | 各故事 DoD |
| C2／C3 | 不追溯 |

## 開放給設計

承 requirements OQ-1～OQ-5。稽核 HTTP 路徑、小數位。時數區間已由本 stage Q6 鎖定為整數 0–24（含）；C1-1 拆分已由本 stage Q5 定案為七則 Must。

---

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-19T07:42:45Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | C1-5 AC-5.7 / C1-6 AC-6.3 | 稽核查詢路徑為佔位符「路徑於 OpenAPI 定案後填入；未定案前人工查 DB 列」，兩個 AC 共享同一根因。QA 在 application-design 定案前無法撰寫自動化稽核查詢測試，只能人工查 DB。稽核內容（操作者、時間、圖 id、舊值、新值）已完整定義，寫入側不受阻。 | application-design 完成後，AC-5.7 與 AC-6.3 補入正式 HTTP 路徑，並設為 construction 前的 blocking check；現有措辭已正確說明暫定可接受。 |
| 2 | Minor | AC-1.1 vs FR-5.1 | AC-1.1 用「系統管理」，FR-5.1 用「Admin」，指向同一 Sidebar 區塊。若 Playwright 以文字定位，兩份文件不一致可能令實作者無所適從。 | 確認 Sidebar 實際標題後，AC-1.1 與 FR-5.1 統一使用相同標籤（「Admin」或「系統管理」擇一）。 |
| 3 | Minor | C1-2「涵蓋」 | AC-2.4「第二人同一總額」對應 FR-7.2，但 C1-2 的「涵蓋」欄未列 FR-7.2，追溯表局部不完整，審查者難以一次確認全部 FR 覆蓋狀況。 | C1-2「涵蓋」補上 FR-7.2。 |
| 4 | Minor | FR-2.2 行為 / C1-1、C1-2 DoD | FR-2.2 要求無公開免帳號端點的雲不呼叫官方價 API。AC-1.6 測試了顯示行為（「所屬雲無公開免帳號價目」→「N 項尚未定價」），但「不發出 API 請求」的約束（防多餘出站 HTTPS）未在任何 AC 或 DoD 中以可驗證斷言呈現。 | 在 C1-2 DoD 補入：「走全 Manual Override 雲的列不得觸發官方價 HTTP 請求（stub 驗零次呼叫）」。 |

### Summary

七則 Must 故事結構嚴謹：角色—權限交叉（Alex／David／Hannah 的 deny／allow AC 成對且無錯位）、0–24 時數區間（AC-4.8）、第一段禁橫幅（AC-1.16）、空狀態與錯誤狀態（AC-1.3、AC-1.13、AC-1.14、AC-2.5、AC-5.2）均已寫入；C2／C3 無漏入；追溯表完整覆蓋 FR-1～FR-8 與全部 NFR。零 Critical、零 Major，四項 Minor 均為術語統一或 DoD 補充，不阻擋工程開始。
