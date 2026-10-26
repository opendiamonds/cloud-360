## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-00 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-generation-plan.md > review findings table | The reviewer's findings table could not be read, so its rows are not listed here: aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-generation-plan.md: findings table header declares ID, Severity, Location, Finding, Status. Expected columns: ID, Severity, Location, Finding, Required action, Status. Missing: Required action | Address the reviewer's findings as written below this table. | Resolved (reviewer) |
| R-01 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 六、偏離與未驗項 第 2 列 | 該列寫「`unit-test-instructions.md` 為已核可內容，未改」，但工作樹 diff 顯示該檔新增了 §四之三（+12 行）。同一節還把案例編為 E11–E13，spec 註解與 traceability.json 卻用 `MB6-E11`–`MB6-E13`，同一組案例在兩份文件叫不同名字。 | 更正該列的陳述（檔案有改，改了什麼），並讓 unit-test-instructions §四之三 的案例標號與 spec／traceability 一致（改用 `MB6-` 前綴，或在表內註明對照）。 | Unresolved |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 五、已接受風險；frontend/src/components/memory/MemoryZone.tsx > deleteRecord 註解 | 風險描述只涵蓋「更早的記憶被刪除使該則滑到前一頁」。實作其實是以 id 比對（`data.some(r => r.memory_id === memoryId)`），所以誤判的條件是該則離開了被重讀的那一頁。另一個方向沒寫：情節區在兩次請求之間若有 2 筆以上的新記憶寫入（agent 會寫入），該則會被推到探測列 limit=21 以外，同樣被判為已刪除。誤判仍需「404 本身是假的」同時發生，機率低，嚴重度如實，但描述不完整。 | 把「往後位移超過探測列」補進已接受風險；選擇性的低成本強化是情節區重讀未命中時再讀相鄰頁（或從 offset 0 重讀）再下結論。 | Unresolved |
| R-03 | Minor | frontend/tests/e2e/memory-page.spec.ts > MB6-E11–E13；code-summary.md > 六 第 1 列 | 偏離說明「以按下確認那一刻的頁重讀，而非 404 到達時的頁」是刻意的設計選擇，但三支新案例都沒有覆蓋「DELETE 在途時翻頁」。若日後把 rowPage 改回讀目前頁，三案都仍綠。 | 加一個 e2e（DELETE 延遲、期間翻頁、404 後斷言重讀的 offset 為原頁），或在偏離說明中明記此選擇未被測試鎖住。 | Unresolved |
| R-04 | Minor | frontend/tests/e2e/memory-page.spec.ts > MB6-E13 的 `@api GET ... -> 500` | 500 不在 OpenAPI 宣告集合，產生 tcms_validate WARN。保留 WARN 並說明理由是可接受的處置；但確認重讀失敗用 `route.abort()` 模擬網路失敗可以完全避開這個 WARN，且前端的 `catch` 路徑相同。 | 可選：改用連線失敗模擬，或維持現狀並在 stage 閘門上逐項呈現此 WARN。 | Unresolved |
| R-05 | Minor | code-summary.md > 六 第 5 列 | §二、§六 兩處已被其他單元的修正推翻（`HierarchyFacade` 缺口已修、`MemoryForbidden` 不再降級），但只在表內註記「原文不回改」，文件頭沒有提示，讀者從上往下會先讀到過期內容。本單元的 code-summary 是本單元自己的產出，不是已核可上游。 | 在過期段落旁加一行就地標註（保留原文、標明已被推翻及依據），或更新該段。 | Unresolved |
| R-06 | Minor | frontend/src/components/memory/MemoryZone.tsx > handleRemoved 的語意／程序區分支（`headingRef.current?.focus()`） | 語意與程序區的刪除完成後，不論焦點目前在哪裡，一律把焦點拉回區標題。情節區已有「只在被刪列就在畫面上那一頁才搬焦點」的判斷，這兩區沒有。若使用者在第一則的 DELETE 在途時，已對另一則按下刪除並停在它的確認鍵上，第一則完成時焦點會被搶走。DELETE 在途時間通常很短，影響小。 | 語意與程序區也只在焦點仍落在該列內或落在 `body` 時才搬焦點，或在 code-summary 明記這是已知取捨。 | New |
| R-07 | Minor | frontend/src/components/memory/MemoryItem.tsx > handleConfirm 與 DeleteConfirmRow 卸載 | 按下確認鍵後，`itemState` 立即變成 `deleting`，確認列卸載，刪除入口重新出現但是 `disabled`。這段期間焦點落在 `body`。成功時由區塊移到區標題，失敗時回到刪除鍵，所以最終落點都正確，中間只有一小段焦點遺失。這是 code-summary 列出的候選 (1)，我判為 Minor，不是 Major。 | 可在 `deleting` 期間讓列本身（`li`）暫時接焦點，或在 code-summary 記為已知。不阻擋。 | New |
| R-08 | Minor | frontend/src/components/Sidebar.tsx > 「我的記憶」的 `<nav>`（約 :247） | 這個 `<nav>` 沒有 `aria-label`，而「入口」「專案」的有。同一側欄裡另有兩個既有的無標籤 `<nav>`（架構與成本群組）。axe 的 `landmark-unique` 屬於 best-practice 規則，`a11y.spec.ts` 的 WCAG 標籤集合不執行它，所以閘門不會紅。這是 code-summary 列出的候選 (2)，我判為 Minor，不是 Major。 | 為此 `<nav>` 加上 `aria-label="我的記憶"`，成本為零。 | New |

> R-00 Reviewer note: 這是上一輪審查檔無法解析的佔位項。本輪的審查檔格式完整，逐項對照後重新記錄，不再有未讀取的發現。

> R-01 Reviewer note: `code-summary.md` 重做章節前的偏離表第 2 列仍寫「`unit-test-instructions.md` 為已核可內容，未改」，但 `git diff --stat` 顯示該檔有 +12 行（§四之三）。案例仍以 E11–E13 與 spec 的 `MB6-E11`–`E13` 兩套名稱並存。陳述仍與事實不符，不影響行為。

> R-02 Reviewer note: `MemoryZone.tsx` 的 `deleteRecord` 註解與 `code-summary.md` 的已接受風險仍只寫「更早的記憶被刪除使該則滑到前一頁」。我另外確認：該判定以 id 比對，情節區在兩次請求之間若新增 2 筆以上記憶，該則會被推出 `limit=21` 之外而被判為已刪除。合併阻擋表第 6 列的審查後補記已涵蓋這一點，但程式註解與 code-summary 沒有。機率低、後果與裁決前相同。

> R-03 Reviewer note: `memory-page.spec.ts` 的三個 `MB6-E11`–`E13` 都沒有「DELETE 在途時翻頁」的情境。我讀過這三案，確認若 `rowPage` 改為讀目前頁，三案仍會綠。計畫已把此選擇列為刻意設計，但沒有任何測試鎖住它。

> R-04 Reviewer note: `MB6-E13` 仍以 `getHook` 回 500 模擬重讀失敗，500 不在 OpenAPI 宣告集合，會產生 tcms_validate WARN。前端 catch 路徑相同，改用 `route.abort()` 可消除 WARN。

> R-05 Reviewer note: `code-summary.md` 的 §二第一點與 §六第一列仍保留已被推翻的敘述，只在偏離表第 5 列與重做章節中說明「原文不回改」，原段落旁沒有就地標註。我的核對對象是該單元自己的產出，不是已核可的上游。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest tests.test_memory_pending_authz tests.test_memory_authz tests.test_memory_contract` | 43 OK | 我自己重跑。B1–B9 全綠。 |
| `eslint`（`src/memory`、`src/components/memory`、`src/pages/MemoryPage.tsx`、`tests/e2e/memory-page.spec.ts`） | 無輸出 | 無 error，無 warning。 |
| 手動核對：合併前必修 #6 | 通過 | 見下方摘要。 |
| 手動核對：待核准帳號檢查 | 通過 | 見下方摘要。 |
| 手動核對：XSS 與儲存衛生 | 通過 | `grep` 找不到 `dangerouslySetInnerHTML`、`innerHTML`、`localStorage`、`sessionStorage`。`console.warn` 只記操作名與狀態碼，不含記憶內容。`content` 以 React 文字節點渲染。 |
| 手動核對：team.md 前端 lint 結構規則 | 通過 | `memoryApi.ts` 是純抓取，state 更新都在呼叫端的 `.then/.catch`。初次載入 effect 用 `cancelled`。`setItems` 用 `filter` 回傳新陣列，不就地修改。 |
| Playwright e2e | 未重跑 | 我讀完 `MB6-E11`–`E13`。code-summary 記載本輪對生產建置實跑 18/18，我沒有獨立重跑。 |

### Summary

合併前必修 #6 確實已修正：`memoryApi.ts` 對 404 只回 `'not-found-unconfirmed'`，`MemoryZone.deleteRecord` 以該列所在頁的同一組參數重讀，已不含該則才走移除與播報，仍含或重讀失敗都拋例外、保留該列，而且不遞增 `requestSeq`、不寫 state。三個 e2e 分別對應「重讀不含」「重讀仍含」「重讀失敗」三條分支，各自能被對應的突變變紅。

`_authorize_approved` 在 `write`、`search`、`list_records`、`delete`、`widen_scope`、`list_audit_events` 六個方法的第一行都有呼叫，而且 `delete` 在取列之前判定，所以不會重開 `[D1]`=A 的枚舉 oracle。`B4` 刻意讓 pending 帳號持 `Platform_Admin`，使 403 只能來自核准檢查。`B8` 用 `embed` 的呼叫次數證明 `search` 在取向量之前就被擋下，並附 allow 側對照，所以不會恆真。ADR-0006 的四個面向中，IAM 與 audit logging（`reason=pending` 拒絕日誌）都有落點，encryption 與 network exposure 不受影響。

我沒有找到 Critical 或 Major。所有新發現與沿用的舊發現都是 Minor，主要是 code-summary 的陳述與事實不符，以及兩個小的焦點與 landmark 細節。
