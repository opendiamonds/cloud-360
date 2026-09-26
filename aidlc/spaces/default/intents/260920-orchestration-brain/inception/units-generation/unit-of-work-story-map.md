# Unit of Work Story Map — 統一入口大腦

<!-- Stage: units-generation（Inception 2.7）· Record: 260920-orchestration-brain -->

## 讀法

把 `stories.md` 的 **20 則故事**對應到本站的 **17 個單元**。中間一欄
是 `domain-design` 的 `traceability.json` 已建立的「故事 → 元件」對應，本檔在其上
再加一層「元件 → 單元」，使追溯鏈完整：**故事 → 元件 → 單元 → 目錄**。

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
| `US1.1` | `IntentRouter`、`WorkItem` | U11 intent-router, U12 work-orchestrator, U14 entry-page-ui | `construction/u11-intent-router/`<br>`construction/u12-work-orchestrator/`<br>`construction/u14-entry-page-ui/` |
| `US1.2` | `IntentRouter` | U11 intent-router, U2 brain-ws-contract, U14 entry-page-ui | `construction/u11-intent-router/`<br>`construction/u2-brain-ws-contract/`<br>`construction/u14-entry-page-ui/` |
| `US1.3` | `WorkOrchestrator`、`WorkItem` | U12 work-orchestrator, U14 entry-page-ui | `construction/u12-work-orchestrator/`<br>`construction/u14-entry-page-ui/` |
| `US1.4` | `BrainGateway` | U3 rbac-story-ids, U14 entry-page-ui | `construction/u3-rbac-story-ids/`<br>`construction/u14-entry-page-ui/` |
| `US2.1` | `SessionContext`、`BrainSession` | U10 session-store, U1 brain-infra, U14 entry-page-ui | `construction/u10-session-store/`<br>`construction/u1-brain-infra/`<br>`construction/u14-entry-page-ui/` |
| `US2.2` | `SessionContext` | U10 session-store, U14 entry-page-ui | `construction/u10-session-store/`<br>`construction/u14-entry-page-ui/` |
| `US3.1` | `SessionContext` | U10 session-store, U14 entry-page-ui | `construction/u10-session-store/`<br>`construction/u14-entry-page-ui/` |
| `US4.1` | `MemoryStore` | U5 memory-data, U8 memory-service, U6 embedding-port | `construction/u5-memory-data/`<br>`construction/u8-memory-service/`<br>`construction/u6-embedding-port/` |
| `US4.2` | `MemoryStore` | U8 memory-service, U15 memory-page-ui, U9 memory-purge | `construction/u8-memory-service/`<br>`construction/u15-memory-page-ui/`<br>`construction/u9-memory-purge/` |
| `US4.3` | `MemoryStore`、`MemoryAuditEvent` | U8 memory-service | `construction/u8-memory-service/` |
| `US4.4` | `MemoryStore` | U8 memory-service, U15 memory-page-ui | `construction/u8-memory-service/`<br>`construction/u15-memory-page-ui/` |
| `US4.5` | `MemoryStore` | U5 memory-data | `construction/u5-memory-data/` |
| `US5.1` | `IntentRouter`、`WorkItem` | U11 intent-router, U12 work-orchestrator, U14 entry-page-ui | `construction/u11-intent-router/`<br>`construction/u12-work-orchestrator/`<br>`construction/u14-entry-page-ui/` |
| `US6.1` | `IntentRouter`、`SessionContext` | U11 intent-router, U10 session-store | `construction/u11-intent-router/`<br>`construction/u10-session-store/` |
| `US7.1` | `BrainGateway` | U13 brain-gateway | `construction/u13-brain-gateway/` |
| `US8.1` | `BrainGateway` | U2 brain-ws-contract, U13 brain-gateway, U14 entry-page-ui | `construction/u2-brain-ws-contract/`<br>`construction/u13-brain-gateway/`<br>`construction/u14-entry-page-ui/` |
| `US9.1` | `ProjectHierarchy` | U4 hierarchy-data, U10 session-store, U14 entry-page-ui | `construction/u4-hierarchy-data/`<br>`construction/u10-session-store/`<br>`construction/u14-entry-page-ui/` |
| `US9.2` | `ProjectHierarchy` | U7 hierarchy-service, U16 object-picker-ui, U3 rbac-story-ids | `construction/u7-hierarchy-service/`<br>`construction/u16-object-picker-ui/`<br>`construction/u3-rbac-story-ids/` |
| `US10.1` | `WorkOrchestrator` | U12 work-orchestrator, U14 entry-page-ui | `construction/u12-work-orchestrator/`<br>`construction/u14-entry-page-ui/` |
| `US10.2` | `WorkOrchestrator`、`WorkItem` | U12 work-orchestrator, U14 entry-page-ui | `construction/u12-work-orchestrator/`<br>`construction/u14-entry-page-ui/` |

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
| U14 entry-page-ui | `US8.1` → `US1.1` → `US1.2` → `US1.3` → `US2.2` → `US5.1` → `US9.1` → `US10.1` → `US10.2` → `US1.4` | 串流（8.1）是畫面的載體，先有它其餘才看得見；`US1.4` 的權限瀑布放最後，因它改的是落地行為而非頁內行為 |
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
