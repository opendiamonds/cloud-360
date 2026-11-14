# Unit of Work Story Map — 統一入口大腦

<!-- Stage: units-generation（Inception 2.7）· Record: 260920-orchestration-brain -->

## 讀法

把 `stories.md` 的 **20 則故事**對應到本站的 **17 個單元**。中間一欄
是 `domain-design` 的 `traceability.json` 已建立的「故事 → 元件」對應，本檔在其上
再加一層「元件 → 單元」，使追溯鏈完整：**故事 → 元件 → 單元 → 目錄**。

> **修訂 4 起這兩個數字為 31 則故事 ／ 24 個單元**（見本檔末尾的「修訂 4」節）。
> 上段保留為修訂 1–3 的歷史敘述，不回改。
>
> **Directory 欄的命名法亦在修訂 4 更正（審查 `R-01`，Critical）**：全檔 67 處
> `construction/u<N>-<name>/` 改為 `construction/<name>/`。理由是引擎與磁碟都用裸單元名
> （`ls construction/` 實為 `brain-infra` 等，無 `u<N>-` 前綴；引擎於
> `aidlc-lib.ts:10032-10033`、`aidlc-orchestrate.ts:2118`／`:2617`、
> `aidlc-swarm.ts:746`／`:788` 三處獨立地以裸單元名組路徑），而 stage 檔
> `units-generation.md:96` 的 `u{n}-{description}` 與之不一致——以引擎為準。
> 完整論證與交接事項 `UG-7` 見 `unit-of-work.md` 的修訂 4 節。

> **`traceability.json` 只記主要落點，本檔表格才是完整映射**（修訂 3 補記，來自審查
> R-07）：`traceability` sensor 的 schema 對 `coverage[].target` 只允許**單一字串**
> （`aidlc-sensor-traceability.ts:15,122`），無法表達一則故事橫跨多個單元，所以
> manifest 每則故事只記**第一個**單元。20 則故事中有 **17 則**實際指派給多於一個
> 單元（實算：`target` 與本檔第一個單元 20／20 相符，無任何 `target` 落在本檔清單
> 之外）。因此**只讀 `traceability.json` 會低估落點**——例如 `US1.1` 在 manifest 只
> 見 `U11`，本檔實為 `U11`／`U12`／`U14`。權威的故事 → 單元映射是下方表格，不是
> manifest。
>
> **一處命名撞號的提醒**：本檔的 `U1`…`U17` 是**單元** id（stage 檔要求的形狀）；
> `user-stories` 那一站的問題編號也叫 `U1`–`U9`。兩者形狀相同、意義不同。本檔的裸
> `U{n}` 一律指單元；指該站問題時一律寫 `[US:U<n>]`。

## 故事 → 單元

> 「實作單元」欄刻意**不用反引號包住、以半角逗號分隔**：`traceability` sensor 的
> `tokenPresent` 只接受 token 前後為空白／`,`／`;`／`/` 或字串邊界，反引號與全角
> 「、」都不在允許的分隔符內，會讓整張表被判為「無任何 story-to-unit 對應」。
> 這是格式要求而非美感選擇。


| Story | 元件（domain-design） | 實作單元 | 目錄 |
|---|---|---|---|
| `US1.1` | `IntentRouter`、`WorkItem` | U11 intent-router, U12 work-orchestrator, U14 entry-page-ui | `construction/intent-router/`<br>`construction/work-orchestrator/`<br>`construction/entry-page-ui/` |
| `US1.2` | `IntentRouter` | U11 intent-router, U2 brain-ws-contract, U14 entry-page-ui | `construction/intent-router/`<br>`construction/brain-ws-contract/`<br>`construction/entry-page-ui/` |
| `US1.3` | `WorkOrchestrator`、`WorkItem` | U12 work-orchestrator, U14 entry-page-ui | `construction/work-orchestrator/`<br>`construction/entry-page-ui/` |
| `US1.4` | `BrainGateway` | U3 rbac-story-ids, U14 entry-page-ui | `construction/rbac-story-ids/`<br>`construction/entry-page-ui/` |
| `US2.1` | `SessionContext`、`BrainSession` | U10 session-store, U1 brain-infra, U14 entry-page-ui | `construction/session-store/`<br>`construction/brain-infra/`<br>`construction/entry-page-ui/` |
| `US2.2` | `SessionContext` | U10 session-store, U14 entry-page-ui | `construction/session-store/`<br>`construction/entry-page-ui/` |
| `US3.1` | `SessionContext` | U10 session-store, U14 entry-page-ui | `construction/session-store/`<br>`construction/entry-page-ui/` |
| `US4.1` | `MemoryStore` | U5 memory-data, U8 memory-service, U6 embedding-port | `construction/memory-data/`<br>`construction/memory-service/`<br>`construction/embedding-port/` |
| `US4.2` | `MemoryStore` | U8 memory-service, U15 memory-page-ui, U9 memory-purge | `construction/memory-service/`<br>`construction/memory-page-ui/`<br>`construction/memory-purge/` |
| `US4.3` | `MemoryStore`、`MemoryAuditEvent` | U8 memory-service | `construction/memory-service/` |
| `US4.4` | `MemoryStore` | U8 memory-service, U15 memory-page-ui | `construction/memory-service/`<br>`construction/memory-page-ui/` |
| `US4.5` | `MemoryStore` | U5 memory-data | `construction/memory-data/` |
| `US5.1` | `IntentRouter`、`WorkItem` | U11 intent-router, U12 work-orchestrator, U14 entry-page-ui | `construction/intent-router/`<br>`construction/work-orchestrator/`<br>`construction/entry-page-ui/` |
| `US6.1` | `IntentRouter`、`SessionContext` | U11 intent-router, U10 session-store | `construction/intent-router/`<br>`construction/session-store/` |
| `US7.1` | `BrainGateway` | U13 brain-gateway | `construction/brain-gateway/` |
| `US8.1` | `BrainGateway` | U2 brain-ws-contract, U13 brain-gateway, U14 entry-page-ui | `construction/brain-ws-contract/`<br>`construction/brain-gateway/`<br>`construction/entry-page-ui/` |
| `US9.1` | `ProjectHierarchy` | U4 hierarchy-data, U10 session-store, U14 entry-page-ui | `construction/hierarchy-data/`<br>`construction/session-store/`<br>`construction/entry-page-ui/` |
| `US9.2` | `ProjectHierarchy` | U7 hierarchy-service, U16 object-picker-ui, U3 rbac-story-ids | `construction/hierarchy-service/`<br>`construction/object-picker-ui/`<br>`construction/rbac-story-ids/` |
| `US10.1` | `WorkOrchestrator` | U12 work-orchestrator, U14 entry-page-ui | `construction/work-orchestrator/`<br>`construction/entry-page-ui/` |
| `US10.2` | `WorkOrchestrator`、`WorkItem` | U12 work-orchestrator, U14 entry-page-ui | `construction/work-orchestrator/`<br>`construction/entry-page-ui/` |

## 跨多個單元的故事（cross-cutting）

共 **17** 則故事橫跨 2 個以上單元。這不是缺陷——多數故事是端到端的垂直
切片（`product-guide.md` 的 vertical slices 原則），必然同時觸及後端與前端。
**但它對 2.9 有直接後果**：一則橫跨 N 個單元的故事，要等那 N 個單元都完成才算可
驗收，故它不能被拆到不同的 Bolt 裡而各自宣稱完成。

| Story | 橫跨的單元 | 數 |
|---|---|---|
| `US1.1` | U11 intent-router, U12 work-orchestrator, U14 entry-page-ui | 3 |
| `US1.2` | U11 intent-router, U2 brain-ws-contract, U14 entry-page-ui | 3 |
| `US1.3` | U12 work-orchestrator, U14 entry-page-ui | 2 |
| `US1.4` | U3 rbac-story-ids, U14 entry-page-ui | 2 |
| `US2.1` | U10 session-store, U1 brain-infra, U14 entry-page-ui | 3 |
| `US2.2` | U10 session-store, U14 entry-page-ui | 2 |
| `US3.1` | U10 session-store, U14 entry-page-ui | 2 |
| `US4.1` | U5 memory-data, U8 memory-service, U6 embedding-port | 3 |
| `US4.2` | U8 memory-service, U15 memory-page-ui, U9 memory-purge | 3 |
| `US4.4` | U8 memory-service, U15 memory-page-ui | 2 |
| `US5.1` | U11 intent-router, U12 work-orchestrator, U14 entry-page-ui | 3 |
| `US6.1` | U11 intent-router, U10 session-store | 2 |
| `US8.1` | U2 brain-ws-contract, U13 brain-gateway, U14 entry-page-ui | 3 |
| `US9.1` | U4 hierarchy-data, U10 session-store, U14 entry-page-ui | 3 |
| `US9.2` | U7 hierarchy-service, U16 object-picker-ui, U3 rbac-story-ids | 3 |
| `US10.1` | U12 work-orchestrator, U14 entry-page-ui | 2 |
| `US10.2` | U12 work-orchestrator, U14 entry-page-ui | 2 |

## 覆蓋驗證

> **修訂 1（審查 R-01 後）**：`US3.1` 原指派 `U10, U16`，但該故事的 AC 要求「由**脈絡元件**
> 選『改為獨立對話』」，而該控件在 `ContextBar` 內、`ContextBar` 歸 `U14`（`U16` 的
> 交付逐字只有「切換對象選單 ＋ 建立表單 ＋ `CreateConfirmCard`」）。已改為 `U10, U14`。
> **另外自查出審查未提的第二列**：`US2.1` 的三條 AC 皆為脈絡列的跨頁顯示，原指派
> `U10, U1` 亦漏 `U14`，一併補上。查法是把 `stories.md` 中提及「脈絡列」或
> `ContextBar` 的故事全部列出、逐列比對 story-map 有無 `U14`——`US3.1` 因用詞是
> 「脈絡元件」而不在該 grep 命中內，故兩種寫法都要查。


| Unit | 承載的故事 | 則數 |
|---|---|---|
| U1 brain-infra | `US2.1` | 1 |
| U2 brain-ws-contract | `US1.2`、`US8.1` | 2 |
| U3 rbac-story-ids | `US1.4`、`US9.2` | 2 |
| U4 hierarchy-data | `US9.1` | 1 |
| U5 memory-data | `US4.1`、`US4.5` | 2 |
| U6 embedding-port | `US4.1` | 1 |
| U7 hierarchy-service | `US9.2` | 1 |
| U8 memory-service | `US4.1`、`US4.2`、`US4.3`、`US4.4` | 4 |
| U9 memory-purge | `US4.2` | 1 |
| U10 session-store | `US2.1`、`US2.2`、`US3.1`、`US6.1`、`US9.1` | 5 |
| U11 intent-router | `US1.1`、`US1.2`、`US5.1`、`US6.1` | 4 |
| U12 work-orchestrator | `US1.1`、`US1.3`、`US5.1`、`US10.1`、`US10.2` | 5 |
| U13 brain-gateway | `US7.1`、`US8.1` | 2 |
| U14 entry-page-ui | `US1.1`、`US1.2`、`US1.3`、`US1.4`、`US2.1`、`US2.2`、`US3.1`、`US5.1`、`US8.1`、`US9.1`、`US10.1`、`US10.2` | 12 |
| U15 memory-page-ui | `US4.2`、`US4.4` | 2 |
| U16 object-picker-ui | `US9.2` | 1 |
| U17 a11y-gate | **（無故事）** | 0 |

**每一則故事都已指派**（20 / 20）。**16 個單元有故事**，
1 個沒有：`U17` `a11y-gate`。

### 沒有故事的單元為什麼仍然存在

- **`U17` `a11y-gate`**（`packaging`）：它承載的是**機制**而非使用者可見行為，故沒有 `USx.y` 對應。這是 `requirements.md` 的回補項所預期的形狀——N-1／N-2／N-9／N-11 逐項說明「這是保護／驗證能力的機制，不在 10 項能力內」。它的完成判準是其驗證方式本身（見 `unit-of-work.md`），不是任何一條 AC。

## 單元內的故事實作順序

依 stage 檔要求列出，但**僅限單元內部**——跨單元的順序是 2.9 的事，本檔不涉及。

| Unit | 單元內建議的故事順序 | 理由 |
|---|---|---|
| U8 memory-service | `US4.1` → `US4.4` → `US4.2` → `US4.3` | 先有寫入與檢索（4.1），才有「我的記憶是我的」的可見範圍（4.4）；刪除（4.2）與稽核查詢（4.3）建立在前兩者的資料之上 |
| U11 intent-router | `US1.1` → `US1.2` → `US6.1` → `US5.1` | 先有成功路徑（1.1）才驗得出失敗路徑（1.2）；多輪（6.1）與多意圖（5.1）都是在單輪單意圖成立之後的擴充 |
| U12 work-orchestrator | `US1.1` → `US1.3` → `US5.1` → `US10.1` → `US10.2` | 工作項要先能產生（1.1）才能被導回（1.3）；多意圖（5.1）是 N 個工作項；成本（10.x）是特定能力的轉譯 |
| U14 entry-page-ui | `US8.1` → `US1.1` → `US1.2` → `US1.3` → **`US2.1` → `US2.2` → `US3.1`** → `US5.1` → `US9.1` → `US10.1` → `US10.2` → `US1.4` | 串流（8.1）是畫面的載體，先有它其餘才看得見；脈絡列那三則（2.1／2.2／3.1）共用同一個 `ContextBar`，放在一起做；`US1.4` 的權限瀑布放最後，因它改的是落地行為而非頁內行為。**修訂 2 補入 `US2.1` 與 `US3.1`**——R-01 把它們加進 `U14` 後，本表是唯一沒跟著重生的衍生表（覆蓋表與跨單元表當時已正確重生） |
| 其餘單元 | 各只承載 0–3 則，無內部排序問題 | — |

## Assumptions & Open Questions

- 「元件 → 單元」的映射由本站建立，其中 `MemoryStore` 落在 2 個單元
  （`memory-data`／`memory-service`）、`ProjectHierarchy` 落在 2 個
  （`hierarchy-data`／`hierarchy-service`）、`BrainGateway` 落在 2 個
  （`brain-gateway`／`entry-page-ui`）——這是 `[UG:G1]`=A 的軸（驗證方式）與
  `domain-design` 的軸（變更理由）不同所致，不是矛盾 [assumption]
- 單元內的故事順序是**開發便利性**的建議，非技術依賴；`project.md` 的
  `scope-definition:rev2-c8` 要求區分兩者，本表全部屬前者，故下游可覆寫 [assumption]
- 橫跨多單元的故事共 17 則，其「不可分批」的判定屬 2.9；本站只列出橫跨事實 [assumption]

---

# 修訂 4（2026-10-03）— `US11`／`US12`／`US13` 共 11 則的映射

修訂 1–3 的 20 則映射**全部有效、不回改**。本修訂補上 `user-stories` 修訂 1 新增的
11 則：`US11.1`–`US11.4`、`US12.1`–`US12.6`、`US13.1`。

**實測基準**：`stories.md` 有 **31 則**故事（`^### US\d+\.\d+` 計數），本檔修訂前只引用
**20 則**，缺 **11 則**。

## 故事 → 單元（修訂 4 新增 11 列）

> 「實作單元」欄沿用上方表格的格式要求（**不用反引號、半角逗號分隔**），理由同上：
> `traceability` sensor 的 `tokenPresent` 只接受空白／`,`／`;`／`/` 或字串邊界作為分隔符。

| Story | 元件（domain-design） | 實作單元 | 目錄 |
|---|---|---|---|
| `US11.1` | `ProjectHierarchy` | U23 project-pages-ui, U7 hierarchy-service | `construction/project-pages-ui/`<br>`construction/hierarchy-service/` |
| `US11.2` | `RequirementRegistry` | U23 project-pages-ui, U20 requirement-field-service, U18 project-meta-data | `construction/project-pages-ui/`<br>`construction/requirement-field-service/`<br>`construction/project-meta-data/` |
| `US11.3` | `RequirementRegistry` | U20 requirement-field-service, U23 project-pages-ui | `construction/requirement-field-service/`<br>`construction/project-pages-ui/` |
| `US11.4` | `McpBridge` | U21 mcp-bridge | `construction/mcp-bridge/` |
| `US12.1` | `ProjectMembership`、`ProjectMember` | U19 membership-service, U24 member-pages-ui, U18 project-meta-data | `construction/membership-service/`<br>`construction/member-pages-ui/`<br>`construction/project-meta-data/` |
| `US12.2` | `ProjectMembership` | U19 membership-service, U24 member-pages-ui | `construction/membership-service/`<br>`construction/member-pages-ui/` |
| `US12.3` | `ProjectMembership` | U19 membership-service | `construction/membership-service/` |
| `US12.4` | `ProjectMembership`、`ReselectionEvent` | U19 membership-service, U24 member-pages-ui | `construction/membership-service/`<br>`construction/member-pages-ui/` |
| `US12.5` | `ProjectMembership` | U19 membership-service, U24 member-pages-ui | `construction/membership-service/`<br>`construction/member-pages-ui/` |
| `US12.6` | `ProjectMembership`、`ProjectMember` | U19 membership-service, U24 member-pages-ui | `construction/membership-service/`<br>`construction/member-pages-ui/` |
| `US13.1` | `ProgressChannel` | U22 progress-channel | `construction/progress-channel/` |

**三處映射判定的理由（不是機械分配）**：

- **`US12.3` 只落在 `U19` 一個單元**，儘管它的三條 AC 其中兩條（自我降級、自我移出）
  的操作入口在 `U24` 的成員詳情頁。理由：`[US:D-06]` 要求閘門位在三條路徑的**共同
  上游**，而三條 AC 斷言的都是「該動作**被拒絕**並說明原因」——拒絕的判定在
  `U19`，畫面只負責顯示它回的理由。把 `U24` 也列上去會讓「這條 AC 完成了嗎」同時
  指涉兩個單元，而實際只有一個地方會讓它紅燈。
- **`U18 project-meta-data` 承載 `US11.2` 與 `US12.1`**，這不是為了避免空單元。
  `AC11.2.1` 的「未填」判定需要資料層能區分「無列」與「`value` 為 null」
  （`ADR-015`）；`AC12.1.1` 的「清單恰有一列、即我自己」直接讀 `project_members`。
  兩者都是在資料層就可能壞掉的斷言。
- **`US11.1` 列 `U7 hierarchy-service` 而非 `U18`**：它的三條 AC 是「建立系統的動作
  存在／空狀態／計數 0→1」，寫入端是既有 `hierarchy-service` 的系統建立端點
  （`U18` 的三張新表都不含 `systems`，那是 `U4` 的）。

## 覆蓋驗證（修訂 4 重算，腳本從本檔的主表與 yaml 邊塊解析後輸出）

| 項目 | 數值 | 來源 |
|---|---|---|
| `stories.md` 的故事總數 | **31** | `^### US\d+\.\d+` 計數 |
| 本檔已映射的故事數 | **31** | 主表 20 列 ＋ 修訂 4 的 11 列 |
| **未映射的故事** | **0** | 逐一比對後為空集合 |
| 單元總數 | **24** | 解析 `unit-of-work-dependency.md` 的 yaml 邊塊 |
| 承載至少一則故事的單元 | **23** | 以「元件 → 單元」映射逐列累計 |
| **沒有故事的單元** | **1**（`U17 a11y-gate`） | 與修訂 1–3 相同，理由見下方既有的「沒有故事的單元為什麼仍然存在」 |
| 橫跨多個單元的故事 | **25**（既有 17 ＋ 新增 8） | 主表中實作單元數 > 1 的列 |

**七個新單元的承載則數**（腳本輸出）：

| Unit | 承載的故事 | 則數 |
|---|---|---|
| U18 project-meta-data | `US11.2`、`US12.1` | 2 |
| U19 membership-service | `US12.1`、`US12.2`、`US12.3`、`US12.4`、`US12.5`、`US12.6` | 6 |
| U20 requirement-field-service | `US11.2`、`US11.3` | 2 |
| U21 mcp-bridge | `US11.4` | 1 |
| U22 progress-channel | `US13.1` | 1 |
| U23 project-pages-ui | `US11.1`、`US11.2`、`US11.3` | 3 |
| U24 member-pages-ui | `US12.1`、`US12.2`、`US12.4`、`US12.5`、`US12.6` | 5 |

**`U24` 是 5 而非 6**：`US12.3` 只落在 `U19`（理由見上）。這個差一的數字是腳本算出來
的，不是我手寫後再核對——修訂 1 的 `R-10` 與 `user-stories` 的 `R-07` 都是同一種
「先寫數字再補算」的失誤。

## 單元內的故事實作順序（修訂 4 新增兩個單元）

| Unit | 單元內建議的故事順序 | 理由 |
|---|---|---|
| U19 membership-service | `US12.1` → `US12.6` → `US12.2` → `US12.5` → `US12.3` → `US12.4` | 先有建立者自動成為管理者（12.1，單一成員的最小狀態），再有**成功邀請與成功移出**（12.6）——**其餘九條 AC 的 Given 都預設「該專案另有成員」，在 12.6 落地前沒有任何東西產生那個人**（`[US:review-02 R-01]` 的唯一 Critical）；角色變更（12.2）要有第二個人才測得出；邀請被拒（12.5）是 12.6 的失敗面；守門（12.3）需要「唯一管理者」這個狀態；自動改選（12.4）需要 owner 被停用且另有成員 |
| U24 member-pages-ui | `US12.1` → `US12.6` → `US12.2` → `US12.5` → `US12.4` | 與 `U19` 同一條理由鏈的畫面側。橫幅（12.4）放最後，因它的 Given 需要一次真實的自動改選 |
| U23 project-pages-ui | `US11.1` → `US11.2` → `US11.3` | 先有系統可建（11.1）才有欄位可填（11.2），有欄位才有計數可比（11.3） |
| 其餘新單元 | `U18`／`U20` 各 2 則、`U21`／`U22` 各 1 則，無內部排序問題 | — |

**這三列是技術便利性的建議，不是技術依賴**（依 `scope-definition:rev2-c8` 的要求區分），
故下游可覆寫。**唯一的例外是 `US12.1` → `US12.6` 這一段**：它比排序更強——在 `US12.6`
落地前，`U19` 其餘五則故事的 Given 在資料上**不可構造**，不是「順序不佳」而是
「做不出來」。

## 修訂 4 的 Assumptions & Open Questions

- `U23` 的「記憶摘要籤」依賴 `U8 memory-service`，但 `US11.1`–`US11.4` **沒有任何
  一條 AC 涵蓋該籤的行為**；它的來源是 `FR11` 前言承的 `[S12]`=A 四項責任之一與線框的
  三籤結構。本檔如實列出該依賴，不為它編一則故事 [assumption]
- 橫跨多單元的故事由 17 增為 **25** 則，其「不可分批」的判定仍屬 2.9；
  本站只列出橫跨事實。`delivery-planning:c6`（破壞性契約變更與其消費端不得分批）在
  `U19` 身上**首次對既有端點成立**——它改 `user_router.py:673` 的回應契約，而該端點
  的既有消費端是 `AdminPage.tsx`，兩者須同批 [assumption]
- `U17 a11y-gate` 仍是唯一沒有故事的單元。修訂 4 把它的掃描範圍由兩頁擴為四頁，
  但那是交付條件（`[US:D-10]` 的共同 DoD），不是可觀察的使用者行為，故不為它編故事
  ——與修訂 1–3 的判定一致 [assumption]
