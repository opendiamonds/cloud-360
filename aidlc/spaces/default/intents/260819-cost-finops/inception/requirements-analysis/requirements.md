# Requirements — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: requirements-analysis（Inception 2.3）· 來源標籤定義見 requirements-analysis-questions.md 的 ## Sources。
     [Q<n>] 指本 stage 問題檔；[intent:*]／[scope:*]／[feas:*]／[rm:*] 指 ideation；
     [kb:*] 指 codekb；[tp] 指 team-practices。 -->

## 上游輸入

- **intent-statement**（`../../ideation/intent-capture/intent-statement.md`）：報價不可信、C1 成功指標、不做 C2／C3／核准流。
- **scope-document**（`../../ideation/scope-definition/scope-document.md`）：Must (a)–(h)、兩段增量、Won't Have 七項。
- **business-overview**（`aidlc/spaces/default/codekb/cloud/business-overview.md`）：執行時仍是 A1／A3／J；C1 產品面 ABSENT。
- **architecture**（`aidlc/spaces/default/codekb/cloud/architecture.md`）：模組化單體、無 cost bounded context；`COST-*` ≠ TCO。
- **code-structure**（`aidlc/spaces/default/codekb/cloud/code-structure.md`）：無 `*cost*`／`*pricing*` 檔；新模組須新路徑。
- **team-practices**（`../practices-discovery/team-practices.md`）：skeleton off、A／B／C 測試底線、C1 HTTP 403、三層 cost 模組。

## 意圖分析

**目標**：讓雲端架構師在產圖後拿到**可對外說明、且對到圖上元件**的每月 list-price 估價；讓 FinOps／工程主管能設每圖預算並在超支時看見（畫面標示＋進產品橫幅）[intent]。

這不是讀客戶帳單，也不是 WA `COST-*` 啟發式 [kb:architecture]。數字路徑是：擷取列名 → 對到公開 SKU 或未定價 → 公開免帳號價目或 Manual Override → 用每日時數算月費 → 圓餅與總額；第二段再加上每圖預算與超支 [scope]。

被插隊時第一段（(a)–(e)＋對應 (h)）可單獨上線；第二段仍是本輪 Must，不是 Should [scope:Q1]。

## 功能需求

### FR-1 從架構圖擷取可估價列（Must (b)）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-1.1 | 對一張已存架構圖產生估價列，每一列對應一個可估價節點 | 列上的資源名等於該節點去掉 HTML 後的 label；列數等於可估價節點數 [scope (b)] [kb:code-structure] |
| FR-1.2 | 以 label／style 對到本輪維護的公開 SKU 對照表 | 對照表中有唯一命中時，該列帶該 SKU 識別字 [Q1] |
| FR-1.3 | 對不到或一對多的列標為未定價 | 該列小計不進入總額；畫面顯示「N 項尚未定價」，N 等於未定價列數 [feas:Q7] [Q1] |
| FR-1.4 | FinOps 可為未定價列指定 SKU 或覆寫單價 | 指定唯一 SKU 後該列可走官方價；覆寫單價後標 Manual Override 且小計用覆寫值 [intent:Q15] [Q1] |
| FR-1.5 | 每次開啟或重算成本畫面時，以**目前**架構圖 XML 重擷取；列以 mxCell `id` 對齊 | 新增可估價節點後再開成本頁，列數比前一次多 1，新列時數為 24；刪除節點後該 `id` 的列與覆寫消失；只改 label 時同一 `id` 的時數、FinOps 指定 SKU、單價覆寫仍在，資源名改為新 label [feas:Q1] |

**可估價節點（FR-1.1／FR-1.5）**：`mxCell` 且 `edge` 不為 `1`、去掉 HTML 後 label 非空，且 style **不含** `group`、`swimlane`、`container=1`。連線、無文字裝飾、VPC／群組容器不列。

**圖變更對齊規則**：FinOps 已指定 SKU 或已覆寫單價的列，重擷取時**不**用自動對照蓋掉；其餘列每次依 FR-1.2 重跑對照。成本頁不得繼續顯示已從 XML 消失的節點列。

**設計必答**：對照表的維護格式與一對多時的建議清單 UI。不得把 `wa_rule_engine.parse_diagram_summary` 的輸出當成已有 SKU [kb:architecture]。

### FR-2 單價：公開價目或 Manual Override（Must (a)(c)）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-2.1 | 有公開免帳號官方價目的雲，對已對到 SKU 的列查 list price | 該列出現大於 0 的單價，且定價假設顯示來源時間（ISO-8601 UTC）[intent:Q12] [feas:Q2] |
| FR-2.2 | 無公開免帳號端點的雲，該雲所有列本輪不打官方價 | 這些列為未定價，直到 Manual Override；成本畫面仍可開啟 [feas:Q1a] [scope:Q4] |
| FR-2.3 | 官方價失敗或該 SKU 缺價時，列可覆寫且標 Manual Override | **覆寫前**：該列不計入總額，計入「N 項尚未定價」，並顯示文字「官方價取得失敗」（與從未對到 SKU 的未定價列可區分，不只靠顏色）。**覆寫後**：小計 = 覆寫月費（見 FR-3.2）；列上可見「Manual Override」文字，不再顯示「官方價取得失敗」[intent:Q15] [rm:Q4] |
| FR-2.4 | 僅 FinOps 能覆寫單價 | 非 FinOps 角色對單價欄不可編輯；該角色呼叫覆寫 API 得到 403 [feas:Q5] [tp] |
| FR-2.5 | 查價不得使用需雲端帳號的 API | 系統設定與程式不出現 Cost Explorer／Billing／Cost Management 憑證路徑 [intent:Q12] [tp Forbidden] |

(a) 公開價目覆蓋查證的交付物：一份「本輪走官方價 vs 全 Manual Override」的雲別清單，寫進定價假設或同等可見位置，並在 Construction 前凍結 [scope (a)]。

### FR-3 TCO 畫面：總額、圓餅、時數（Must (d)）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-3.1 | 總額等於所有**已定價**列小計之和 | 加入或移除一筆未定價列，總額不變；改一筆已定價列的時數或單價，總額等於新的已定價小計之和 [feas:Q7] |
| FR-3.2 | 列小計（月費）= 小時 list price × 每日時數 × 30；僅有月價的 SKU 以 `月價 / 730` 為小時價 | 時數 24、小時價 1 時小計為 720；僅月價 730 且時數 24 時小計為 720（允許浮點誤差在設計指定的小數位內）[Q6] |
| FR-3.3 | 每日時數預設 24，僅在列上可改；架構師可改 | 新擷取列的時數為 24；無頁面級時數控件；非架構師角色無法改時數（API 403）[Q3] [rm:Q1] [feas:Q5] |
| FR-3.4 | 圓餅四類：compute／database／network／other，對不到的進 other | 圓餅另附文字清單（類別名與該類已定價金額或占比）；四類金額之和等於總額 [Q4] [rm:Q1] |
| FR-3.5 | 顯示定價假設：區域、USD、公式、來源時間 | 畫面同時可見估價區域、幣別 USD、FR-3.2 公式摘要、官方價來源時間 [intent] [Q2] |
| FR-3.6 | 資訊層級：總額置頂 → 圓餅 → 資源列 | 視覺與 heading 順序為 h1 預估成本、h2 圓餅拆解、h2 資源列 [rm:Q1] |

### FR-4 估價區域（本站 Q2）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-4.1 | 每張圖在查官方價之前必須有估價區域；**由架構師設定與修改** | 未設區域時不呼叫官方價；畫面提示必填；已填後假設列與 API 使用同一區域碼。非架構師角色對區域控件不可編輯，該角色呼叫設定／修改區域 API 得到 403 [Q2] [feas:Q5] |
| FR-4.2 | 幣別固定 USD | 所有單價、小計、總額、預算的顯示與儲存單位為 USD，無換匯 [Q2] |

### FR-5 入口（Must (e)）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-5.1 | Sidebar 在「架構」與「Admin」之間有「成本」大類，其下「預估成本」 | 具 C1 view 的使用者看得到該連結；無 C1 view 看不到 [intent:Q13] [kb:business-overview] |
| FR-5.2 | 產圖成功卡有「查看預估成本」，與既有 CTA 並列 | 點擊後進入成本畫面且預選剛產的圖 [rm:Q2] |
| FR-5.3 | 無圖或未選圖時顯示空狀態 | 不捏造總額；提供圖下拉與前往架構圖生成 [rm] |
| FR-5.4 | 有多張圖時以頁首下拉切換 | 切換後總額／列／預算綁定所選圖 [rm] |

### FR-6 每圖預算與超支（Must (f)(g)，第二段）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-6.1 | 每張架構圖一個每月預算上限（USD） | 圖 A 的預算不影響圖 B 的超支判定 [feas:Q4] |
| FR-6.2 | FinOps 與工程主管可編輯預算；架構師不可 | 架構師改預算 API 403；FinOps 或工程主管改成功後讀回值等於寫入值 [feas:Q5] |
| FR-6.3 | 總額 > 預算時，總額旁顯示文字「已超支」且總額變色 | 同時有文字與顏色，不是只靠顏色 [rm:Q3] |
| FR-6.4 | 總額 ≤ 預算（含相等）時不顯示「已超支」 | 預算改到不小於總額後，標籤消失 [feas:Q6] |
| FR-6.5 | 只要使用者可見的圖仍超支，每次進入受保護頁都看到一條橫幅 | 關閉瀏覽器再登入，橫幅仍在；沒有「永遠不要再顯示」[feas:Q6] |
| FR-6.6 | 多圖超支時仍只有一條橫幅：顯示超支圖數量，並點名至少一張 | 「前往成本畫面」預選第一張超支圖 [Q5] |
| FR-6.7 | 橫幅不能永遠關閉；本輪無 inbox | 系統無未讀數、無通知歷史頁 [scope Won't Have] |

第一段上線時 FR-6 可不出現在 UI（預算欄隱藏）[rm:Q6]；整輪完成前 FR-6 必須交付 [scope:Q1]。

### FR-7 持久化

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-7.1 | 時數、SKU 對應、單價覆寫、預算、估價區域、每圖最近總額與超支狀態寫入伺服器 | **第一段**：換瀏覽器、同一帳號再開，時數、SKU 對應、單價覆寫、估價區域仍在；不驗預算與橫幅。**第二段**：另驗預算、每圖最近總額、超支狀態與橫幅仍在 [feas:Q6] [rm:Q6] |
| FR-7.2 | 估價綁定架構圖，不綁使用者個人暫存為唯一來源 | 有權限的第二人開啟同一圖，看到同一總額與預算（覆寫列對有權限角色可見）；列集合遵守 FR-1.5，不出現對方瀏覽器裡已刪節點的列 [intent] |

### FR-8 授權與稽核

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-8.1 | 所有 C1 HTTP 端點以 C1 權限守衛 | 無 C1 view 讀取 → 403；無對應 edit 的變更 → 403 [tp] |
| FR-8.2 | 第一個 C1 HTTP 端點即使種子未改，也有 allow／deny TestClient（交付條件見 DoD） | 行為：有權 2xx、無權 403 [tp] |
| FR-8.3 | 單價覆寫與預算變更留下稽核：誰、何時、哪張圖、舊值、新值 | 變更後可查出一筆對應紀錄，含操作者識別與時間 [feas 合規] |

權限四種變更如何對到既有 view／edit／review 留設計 [feas R2]；本檔只鎖定產品語意 FR-2.4／FR-3.3／FR-4.1／FR-6.2。

## 非功能需求

| # | 面向 | 需求 | 驗收標準 |
| --- | --- | --- | --- |
| NFR-1 | 無障礙 | WCAG 2.1 AA；桌面優先 | 對比 ≥ 4.5:1；鍵盤可達圖下拉、時數、估價區域、覆寫、預算、CTA、橫幅連結；圓餅不單靠圖形 [rm:Q5] |
| NFR-2 | 可用性 | 小螢幕不另做卡片佈局 | 成本頁在窄視窗可捲動讀完總額、圓餅文字清單與表格，不斷開操作 [rm:Q5] |
| NFR-3 | 正確性 | calculator 為純函式，PBT 覆蓋加總、時數公式、未定價排除、覆寫優先於 list price | 性質測試失敗即視為未完成；模組內無 httpx／DB／HTTPException [tp] [ADR-0006] |
| NFR-4 | 效能 | 已快取或已覆寫的圖，打開成本頁在 50 列內於 5 秒內呈現總額 | 計時自已認證的成本頁請求開始，至總額數字出現；不含首次官方價冷查 [設計可訂快取，R5] |
| NFR-5 | 安全 | 見下方四面向表 | 四列皆有判定，不適用者附理由 |

### Security baseline（ADR-0006）

| 面向 | 判定 | 處置 |
| --- | --- | --- |
| IAM | **適用** | C1 路由守衛；四種變更權見 FR-8；種子變更須 allow／deny [tp] |
| Encryption | **沿用既有** | 估價與覆寫走既有 HTTPS 與資料庫加密／磁碟政策，不新公開明文價目憑證；本輪無新瀏覽器端密文需求 |
| Network exposure | **適用** | 僅新增對公開免帳號價目的**出站** HTTPS；不新開入站埠；禁止連到需帳號的計費 API [tp Forbidden] |
| Audit logging | **適用** | FR-8.3：覆寫與預算變更必留稽核 [feas] |

## 約束

- 三層模組：`cost_router` → `cost_service` → `cost_calculator` + `pricing_client`；禁止寫進 `user_router.py`／`wa_rule_engine.py` [tp]
- 文件繁體中文；識別字英文 [ADR-0009]
- 不得使用 production credentials；不得新增 path parts 含 `prod`／`production`／`secrets` [project Forbidden]
- schema／seed 變更同步 `schema_rbac.sql` 與 `DEPLOY.md` [scope (h)]
- OpenAPI 與 generated types 必須與新端點同 PR [kb:code-structure] [tp]

## 假設

- [assumption] 被插隊時第一段單獨上線仍須滿足該段 DoD，不是沒測先上 [scope]
- [assumption] 「進入產品」＝已登入後進入任一受保護頁；橫幅掛在哪些版位留 refined-mockups／設計 [feas]
- [assumption] 30 與 730 為固定換算常數，本輪不提供設定介面 [Q6]
- [assumption] SKU 對照表本輪由團隊維護、隨 repo 或設定發布，不是即時爬蟲百科 [Q1]
- [assumption] 內部估價資料不受 PCI／HIPAA 等外部框架約束 [feas A2]

## 範圍外

與 scope Won't Have 一致：C2、C3、本輪 TCO 的 egress 列、FinOps 核准流、inbox、staging 價目憑證、Cost Explorer／客戶帳單。另：不把 WA `COST-*` 當 TCO；不把 Assessment 雲別下拉當 Manual Override [kb] [tp Forbidden]。

## Definition of Done（測試與部署資產，Must (h)）

這些是交付條件，不是「系統行為」驗收句：

1. `cost_calculator` 含 Hypothesis 性質測試（加總、FR-3.2 公式、未定價排除、覆寫優先）。
2. 每個新／改 C1 HTTP 端點有 TestClient：2xx 欄位集＋無權 403。
3. 若改 C1 `role_permissions` 種子：allow／deny 雙向測試。
4. 新 Cost 頁或 Sidebar C 入口：至少一個 Playwright case 斷言可達與核心欄位可見。
5. 新表／seed：同步 `schema_rbac.sql`、`DEPLOY.md`、必要的 `database.py` ensure。
6. `openapi.json` 與 `frontend/src/types/api.d.ts` 無 CI drift。

## 開放問題（留給設計，不阻本檔）

| ID | 問題 | 去向 |
|---|---|---|
| OQ-1 | view／edit／review 如何表達四種變更權（時數 FR-3.3、區域 FR-4.1、預算 FR-6.2、單價覆寫 FR-2.4） | application-design（feas R2） |
| OQ-2 | 公開價目快取、重試、節流 | application-design（feas R5） |
| OQ-3 | 各雲實際公開端點 URL 與 (a) 覆蓋清單 | PU-1／infrastructure-design |
| OQ-4 | 橫幅在 Layout 的 DOM 位置 | refined-mockups |
| OQ-5 | SKU 對照表檔案格式與一對多建議 UI | application-design |

## 需求對 Must 追溯

| Scope | 需求 |
|---|---|
| (a) 價目覆蓋 | FR-2.2、FR-2.5、覆蓋清單 |
| (b) 擷取 | FR-1 |
| (c) 單價 | FR-2 |
| (d) TCO 畫面 | FR-3、FR-4 |
| (e) 入口 | FR-5 |
| (f)(g) 預算與超支 | FR-6、FR-7 |
| (h) 測試／部署 | DoD |

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-19T07:14:03Z
**Iteration:** 2

### 前次發現追蹤

| # | 前次發現 | 狀態 | 說明 |
|---|---|---|---|
| 1 | Major FR-4.1 — 估價區域缺權限主體 | ✅ 已解決 | FR-4.1 標題加入「**由架構師設定與修改**」；AC 補「非架構師角色對區域控件不可編輯，該角色呼叫設定／修改區域 API 得到 403」；OQ-1 射程同步擴充至 FR-4.1。主體明確，QA 可寫 403 測試。 |
| 2 | Major FR-7.2 / FR-1.1 — 圖修改後估價列行為缺席 | ✅ 已解決 | 新增 FR-1.5 涵蓋三種圖變更場景（新增節點、刪除節點、僅改 label）並以 `mxCell id` 對齊；「圖變更對齊規則」段落定義 FinOps 覆寫與 SKU 指定在重擷取時的保留語意。工程師現有明確的產品決策可實作，不需自行填補。 |
| 3 | Minor FR-2.3 — API 失敗覆寫前狀態 | ✅ 已解決 | FR-2.3 AC 補入「覆寫前」狀態：不計入總額、計入「N 項尚未定價」、顯示「官方價取得失敗」文字，且明定與一般未定價列可區分（不只靠顏色）。 |
| 4 | Minor FR-1.1 — 「具 label 的元件」排除邊界 | ✅ 已解決 | 新增「可估價節點」定義段落：`mxCell` 且 `edge ≠ 1`、去掉 HTML 後 label 非空、style 不含 `group`／`swimlane`／`container=1`；連線、無文字裝飾與容器明文排除。AC 的「列數」現有確定性計算依據。 |
| 5 | Minor FR-7.1 — 第一段 AC 含橫幅與第二段不一致 | ✅ 已解決 | FR-7.1 AC 拆為「第一段」（不驗預算與橫幅）與「第二段」（另驗預算、總額、超支狀態與橫幅），與 DoD 第 93 行的分段描述對齊，不再矛盾。 |

### 新發現

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | FR-6.6 | 「第一張超支圖」排序未定義。AC 說「前往成本畫面預選第一張超支圖」，但未定義「第一張」的排序依據（建立時間、超支金額、圖名稱字母序均為可能實作）。QA 在多圖同時超支時無法寫出確定性的「預選哪張」斷言。 | 在 FR-6.6 AC 或 OQ 補一句：例如「第一張依建立時間升冪」或「依超支金額降冪」；或在開放問題新增 OQ-6 留給 application-design 決定，並把 AC 改為「預選其中一張超支圖（具體排序見設計）」以避免虛假精確性。 |
| 2 | Minor | FR-7.2 | 「有權限角色」對覆寫列的可見範圍未例舉。FR-7.2 AC 括弧說「覆寫列對有權限角色可見」，但未定義「有權限」是所有持 C1 view 的角色，還是僅限 FinOps。若架構師或工程主管開啟同一圖，他們看到的覆寫單價是否可見，將影響 FR-8.1 的 view 守衛設計。不影響 Major 判定，因合理預設（C1 view 皆可見估價含覆寫值）可讓工程師無阻擋前進，但應在 application-design 顯式確認。 | 在 OQ-1 或 FR-7.2 補一句：「C1 view 持有者均可讀取覆寫後的單價顯示；覆寫操作權仍限 FinOps（FR-2.4）」，或將此問題加入 OQ-1 射程。 |

### Summary

感測器兩項全過；兩項前次 Major 均已完整解決：FR-4.1 補入架構師為明確主體並加入 403 AC，FR-1.5 全面定義三種圖變更場景及 Manual Override 保留語意。三項前次 Minor 亦同步修補完畢。本版零 Critical、零 Major，兩項新 Minor（FR-6.6 排序與 FR-7.2 角色可見範圍）均為可在 application-design 階段補齊的設計細節，不阻擋工程開始。文件已達「工程師可以開始實作而不需返回詢問」的標準。
