## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-00 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-generation-plan.md > review findings table | The reviewer's findings table could not be read, so its rows are not listed here: aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-generation-plan.md: findings table header declares ID, Severity, Location, Finding, Status. Expected columns: ID, Severity, Location, Finding, Required action, Status. Missing: Required action | Address the reviewer's findings as written below this table. | Resolved (reviewer) |
| R-01 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 六、偏離與未驗項 第 2 列 | 該列寫「`unit-test-instructions.md` 為已核可內容，未改」，但工作樹 diff 顯示該檔新增了 §四之三（+12 行）。同一節還把案例編為 E11–E13，spec 註解與 traceability.json 卻用 `MB6-E11`–`MB6-E13`，同一組案例在兩份文件叫不同名字。 | 更正該列的陳述（檔案有改，改了什麼），並讓 unit-test-instructions §四之三 的案例標號與 spec／traceability 一致（改用 `MB6-` 前綴，或在表內註明對照）。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 五、已接受風險；frontend/src/components/memory/MemoryZone.tsx > deleteRecord 註解 | 風險描述只涵蓋「更早的記憶被刪除使該則滑到前一頁」。實作其實是以 id 比對（`data.some(r => r.memory_id === memoryId)`），所以誤判的條件是該則離開了被重讀的那一頁。另一個方向沒寫：情節區在兩次請求之間若有 2 筆以上的新記憶寫入（agent 會寫入），該則會被推到探測列 limit=21 以外，同樣被判為已刪除。誤判仍需「404 本身是假的」同時發生，機率低，嚴重度如實，但描述不完整。 | 把「往後位移超過探測列」補進已接受風險；選擇性的低成本強化是情節區重讀未命中時再讀相鄰頁（或從 offset 0 重讀）再下結論。 | Resolved (reviewer) |
| R-03 | Minor | frontend/tests/e2e/memory-page.spec.ts > MB6-E11–E13；code-summary.md > 六 第 1 列 | 偏離說明「以按下確認那一刻的頁重讀，而非 404 到達時的頁」是刻意的設計選擇，但三支新案例都沒有覆蓋「DELETE 在途時翻頁」。若日後把 rowPage 改回讀目前頁，三案都仍綠。 | 加一個 e2e（DELETE 延遲、期間翻頁、404 後斷言重讀的 offset 為原頁），或在偏離說明中明記此選擇未被測試鎖住。 | Resolved (reviewer) |
| R-04 | Minor | frontend/tests/e2e/memory-page.spec.ts > MB6-E13 的 `@api GET ... -> 500` | 500 不在 OpenAPI 宣告集合，產生 tcms_validate WARN。保留 WARN 並說明理由是可接受的處置；但確認重讀失敗用 `route.abort()` 模擬網路失敗可以完全避開這個 WARN，且前端的 `catch` 路徑相同。 | 可選：改用連線失敗模擬，或維持現狀並在 stage 閘門上逐項呈現此 WARN。 | Resolved (reviewer) |
| R-05 | Minor | code-summary.md > 六 第 5 列 | §二、§六 兩處已被其他單元的修正推翻（`HierarchyFacade` 缺口已修、`MemoryForbidden` 不再降級），但只在表內註記「原文不回改」，文件頭沒有提示，讀者從上往下會先讀到過期內容。本單元的 code-summary 是本單元自己的產出，不是已核可上游。 | 在過期段落旁加一行就地標註（保留原文、標明已被推翻及依據），或更新該段。 | Resolved (reviewer) |
| R-06 | Minor | frontend/src/components/memory/MemoryZone.tsx > handleRemoved 的語意／程序區分支（`headingRef.current?.focus()`） | 語意與程序區的刪除完成後，不論焦點目前在哪裡，一律把焦點拉回區標題。情節區已有「只在被刪列就在畫面上那一頁才搬焦點」的判斷，這兩區沒有。若使用者在第一則的 DELETE 在途時，已對另一則按下刪除並停在它的確認鍵上，第一則完成時焦點會被搶走。DELETE 在途時間通常很短，影響小。 | 語意與程序區也只在焦點仍落在該列內或落在 `body` 時才搬焦點，或在 code-summary 明記這是已知取捨。 | Resolved (reviewer) |
| R-07 | Minor | frontend/src/components/memory/MemoryItem.tsx > handleConfirm 與 DeleteConfirmRow 卸載 | 按下確認鍵後，`itemState` 立即變成 `deleting`，確認列卸載，刪除入口重新出現但是 `disabled`。這段期間焦點落在 `body`。成功時由區塊移到區標題，失敗時回到刪除鍵，所以最終落點都正確，中間只有一小段焦點遺失。這是 code-summary 列出的候選 (1)，我判為 Minor，不是 Major。 | 可在 `deleting` 期間讓列本身（`li`）暫時接焦點，或在 code-summary 記為已知。不阻擋。 | Resolved (reviewer) |
| R-08 | Minor | frontend/src/components/Sidebar.tsx > 「我的記憶」的 `<nav>`（約 :247） | 這個 `<nav>` 沒有 `aria-label`，而「入口」「專案」的有。同一側欄裡另有兩個既有的無標籤 `<nav>`（架構與成本群組）。axe 的 `landmark-unique` 屬於 best-practice 規則，`a11y.spec.ts` 的 WCAG 標籤集合不執行它，所以閘門不會紅。這是 code-summary 列出的候選 (2)，我判為 Minor，不是 Major。 | 為此 `<nav>` 加上 `aria-label="我的記憶"`，成本為零。 | Unresolved |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/code-generation/code-summary.md > 共用檔異動後的重新驗證與補審 > 四 | 限制 L4 至 L6 標示為需新增，但 merge-blockers.md 第 6 列只含 (a) 至 (d)，不含焦點兩項與 aria-label 項；在 conductor 併入前，這三項只存在於本單元紀錄中 | 由 conductor 把 L4 至 L6 併入 merge-blockers.md，或直接為 Sidebar 加上 aria-label 並於下輪處理 L4、L5 | New |

> R-01 Reviewer note: code-summary 重新查驗節 §六 第 2 列已就地更正，並附 E11 至 E13 對照 MB6-E11 至 E13 的說明；spec 與 traceability.json 的 MB6 標號與對照一致

> R-02 Reviewer note: §五 已就地補記往後位移超過探測列的情形，判定為 id 比對與 MemoryZone.tsx 第 235 行相符；程式註解仍只寫往前位移，已以限制 L1 追蹤，merge-blockers 第 6 列補記 (a) 已涵蓋

> R-03 Reviewer note: 已就地註明 rowPage 選擇未被測試鎖住；補測試記為限制 L2，merge-blockers 第 6 列 (b) 已涵蓋

> R-04 Reviewer note: 此項為可選強化；WARN 保留並說明理由，限制 L3 對應第 6 列 (c)

> R-05 Reviewer note: §二 第一點與 §六 第一列旁已加就地標註並保留原文，標註依據的共用檔表與實際相符

> R-06 Reviewer note: 程式未改，已明記為已知取捨（限制 L4）；原發現允許以文件記錄代替修正。實測 MemoryZone.tsx 第 255 行語意與程序區仍無條件移焦點，第 266 行情節區才有條件

> R-07 Reviewer note: 同上，記為已知取捨（限制 L5）；MemoryItem.tsx 第 86 行行為不變

> R-08 Reviewer note: Sidebar.tsx 第 247 行的 nav 仍無 aria-label，第 129 行與第 233 行有；成本為零的修正未做，僅記為限制 L6，且尚未併入 merge-blockers

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| git diff 8cf948c on backend/services/memory_facade.py | 單一 hunk，delete 的 try/except MemoryNotFound，位於取列與擁有者判定之後 | 與開發者宣稱一致；git log 顯示收據後只有 7a50a40 一個提交 |
| 逐行檢查 _authorize_approved 與日誌 | 呼叫位於第 272、315、352、393、435、492 行共六處；reason=pending 日誌在第 197 至 202 行，先記錄再 raise；delete 在第 393 行判定、第 394 行解析 id、第 396 行取列；不存在與非擁有者皆為 MemoryNotFound | 六處、日誌、先判定後取列、D1=A 的 404 收斂皆未被破壞 |
| shasum 比對 reviewed-source-00c3990a7da5.tsv | 僅 memory_facade.py 不符，其餘 19 列含 source-manifest.json 逐位元相同 | 與宣稱一致 |
| 後端三模組（自己的副本，PYTHONDONTWRITEBYTECODE、-B、-P） | Ran 43 tests OK；test_memory_pending_authz 單獨為 9 個 OK | 與宣稱的 43 測試與 9、23、11 分布相符；repo 內未留下新增 .pyc 或 .hypothesis |
| 計畫檔 git diff --numstat 與勾選計數 | 10 0；已勾 22、未勾 0 | 計畫內文只多了四之二的 10 行，22 格全勾，且每格在 code-summary 第五節有對應依據 |
| 行號與 spec 抽查 | MemoryZone.tsx 第 235 行 id 比對、第 255 行與第 266 行焦點、MemoryItem.tsx 第 86 行、Sidebar.tsx 第 129、162、218、233、247、279 行 nav、spec 的 MB6 註解第 889、923、956 行、traceability 第 173、299 行 | 與 code-summary 陳述相符；spec 全檔無 route.abort |

### Summary

本輪未改程式，僅 memory_facade.py 在收據後有單一、與本單元授權路徑無關的 hunk，其餘 19 列逐位元相同，43 個後端測試在獨立副本重跑皆通過，22 格勾選與計畫差異皆有證據。沒有 Critical 或 Major；剩餘為 R-08 的零成本 aria-label 未修，以及 L4 至 L6 尚待併入 merge-blockers 兩個 Minor。
