<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-23T12:51:43Z — Revision 1 重製時，未把 [Q1] 的人工確認延伸到新增的 U-6／U-7。[Q1] 確認的是它作答當下存在的清單，新增項需另問（[Q4]）。若沿用舊確認，artifact 會宣稱使用者接受了他從未看過的項目——這與「不得摘要或代答使用者輸入」是同一條紀律的兩面。
- 2026-08-23T12:51:43Z — 邊界驗證重算後 Intent→Scope 的覆蓋率不變（仍 9／11）。CAP-11 補的是「狀態失真」與「其他協作者」兩項已完整的元素，不碰「可追溯」與「未來的自己」那兩個缺口。誠實記為不變，而不是趁重算把數字說得好看。
- 2026-08-23T06:30:31Z — phase 邊界驗證的產出路徑有兩份上游文件互相不一致：stage 檔 Step 5 與 verification.md 都說 <record>/verification/phase-check-<phase>.md，governance protocol 說 <record>/verification/[phase-boundary]-verification.md。三取二，採 phase-check-ideation.md。此檔未列在 stage 的 produces 清單中，但 Step 5 明確指名了路徑（與 value-stream-map 那種只提名稱不給路徑的情形不同），故建檔而非併入既有 artifact。
- 2026-08-23T06:30:31Z — PHASE_VERIFIED 事件未手寫。governance protocol 說「Log a PHASE_VERIFIED event」，但 audit-format 明載其發出者為 aidlc-state.ts 的 advance／complete-workflow，且 SKILL.md 禁止從 prose 發出 audit 事件。以工具所有權為準，由引擎在核可推進時自行發出。
- 2026-08-23T06:17:10Z — feasibility 核可後取得的新事實，於本站彙整時據以更新交接包的依賴狀態（不回改已核可的上游 artifact）：DEP-2／P-2 已完成——實測 repos/opendiamonds/cloud-360 的 secrets 含 APP_PRIVATE_KEY（2026-08-23T06:11:48Z），variables 僅存 APP_ID，明文那份已移除。DEP-1／P-1 仍未驗證：查詢 org 安裝需 admin:org scope 而 active 帳號無此權限，使用者選擇不單獨驗證，改由 CAP-9／PU-0 的最小可行呼叫一併證明（該呼叫失敗即代表未安裝或無權限）。
- 2026-08-23T06:17:10Z — 期間發現並已修復一項憑證處置缺陷：APP_PRIVATE_KEY 原被存為 Actions variable 而非 secret。variable 為明文、UI 可回讀、且在 workflow log 中不遮罩，而本 repo 為 PUBLIC（Actions log 公開可讀）、有 5 名協作者。實測未認證讀取該端點回 HTTP 401，故未對匿名者外洩。使用者已重新產生私鑰並改存 secret、刪除 variable，風險結案而非僅搬移。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-08-23T12:51:43Z — 本站於首次核可後被回跳重製（Modify）。修訂範圍不只是加欄位：ADR-0013 的四項架構裁決原本只記在非問答決策 E-4 的一格裡，重製時把它們提升為 D-33～D-36 進入決策表。理由是它們是與 Q&A 決策同級的定案，塞在事件描述裡會讓下游查決策時漏掉。
- 2026-08-23T06:30:31Z — 未另設 Consolidated Summary Confirmation 關卡。本站三題皆為結構化選單單選、選項全文於作答當下完整呈現，答案即其字面內容；依 project.md 既有 correction（彙整 artifact 的清單若與問題檔某題的已答內容逐字對應，該題作答即為人工確認），另設一道只是把同一份內容再問一次。理由已寫進問題檔的該段。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-08-23T12:51:43Z — W-4 是回跳修訂的固有後果：scope-definition 在 feasibility 下游，回跳到它不會讓 feasibility 重跑，於是 CAP-11 成為唯一一個繞過可行性評估進入範圍的能力。使用者明示選擇不連帶回跳（[Q4] 選項 B 未被選取），已指派 application-design 補齊。風險在於下游可能把 ADR-0012 的推理誤當成本 intent 已完成的評估——那份推理是為 ADR-0012 自己的設計（intent→Project、scripts 承載）做的，前提與本 intent 已經不同。
- 2026-08-23T06:30:31Z — 邊界驗證查出一個真缺口：成功指標「可追溯」與受益者「未來的自己」都需要歷史軌跡，但十項能力全部只處理當下狀態，無一產生變更歷史。CAP-7 只呈現目前 stage。工作流程執行紀錄雖含時間與來源，但那是附帶產物、非宣告能力，且公開 repo 的紀錄有保存期限。已列為 W-1／W-2 指派 requirements-analysis，但若該站也沒接住，這個指標會一路無人承接到驗收。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
