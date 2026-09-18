<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-09T03:00:00Z — CONDITIONAL 適用性逐項對照 stage 的 condition 條款判定為 Execute：本 intent 為使用者可見的介面變更（Admin 表格加欄）、涉及兩類已確認受益者且權限邊界有跨角色差異，屬 condition 明列的 user-facing features 與 multiple user personas，非其 skip 條款（純重構／孤立 bugfix／純基礎設施／開發者工具）。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-09T04:00:00Z — 三位協作者的 24 項 OBJECT 未走 §5 的 round 2：事實性項目（導覽文字誤述、AC 恆真、既有環境生效缺口、邊界未定義）由 lead 整合時直接吸收，四項判斷題升為人類裁決。round 2 用於專家可裁決的知識爭議，而這批 OBJECT 多為協作者回 repo 實測後補上的事實，無可爭議之處。

- 2026-08-11T00:00:00Z — Revision 1 的 mob 未重跑既有三份 contribution，改以「附加 Revision 1 輪次段落」形式保留 Round 1 原件：Round 1 覆核的是 US-1〜US-4，內容仍然有效且是該輪的永久紀錄；覆寫會讓已核可故事的審查依據消失。三位協作者的 brief 明訂只審 Revision 1 新增部分、且要求自行回 repo 實測而非轉引 lead 敘述。
- 2026-08-11T00:00:00Z — 29 項 OBJECT 未走 §5 的 round 2：其中無一項是專家之間互相矛盾的知識爭議（三方各自從 UX／實作／可測試性切入，結論互補不互斥），全部為「回 repo 實測後補上 lead 沒查到的事實」。round 2 的用途是可裁決的爭議，這批沒有可爭議之處，直接整合。與 practices-discovery 於 2026-08-09 的同型判斷一致。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-09T04:00:00Z — 測試底線的 AC 由「元層次」（Then 存在某測試）改為具體行為 AC，測試要求下放至各故事的 Definition of Done：AC 描述系統行為才可能真的失敗，元層次寫法驗收的是「有沒有寫測試」而非「功能對不對」，且實測證實原寫法照做也抓不到要防的缺陷。此決定成為後續所有故事的 AC 慣例。
- 2026-08-09T04:00:00Z — 恆真的 AC 一律改寫而非刪除：FR-2.5 的防禦意圖是真實的，只是原本落在 UI 層（實碼證明 UI 不可能變空白），改落到 API 契約層才碰得到真正的失敗面。
- 2026-08-09T04:00:00Z — 依賴圖區分「建置依賴」與「驗收依賴」兩類，並額外標示非邏輯依賴的交付序列約束（三則故事動同一段 JSX）：原本單一的依賴概念把三種不同性質的約束混為一談，導致 US-3 同時被標為「US-1 的前提」又自述「可平行開發」。

- 2026-08-11T00:00:00Z — 三條被查出恆真的 AC（AC-5.2 存在性斷言、AC-5.5 兩個互斥結果、AC-5.8 頁次不進入判定路徑）全部改寫落點而非刪除：防禦意圖都是真的，錯的是層次。AC-5.8 的改寫最能說明差別 —— 原本驗「同一帳號在不同頁標示相同」（不可能失敗），改後驗「經分頁切換路徑取得的頁，欄位值與資料庫一致」（分頁 envelope 是新的回應構造點，與已知的漏傳缺陷同型，真的會壞）。
- 2026-08-11T00:00:00Z — AC-5.3（跨頁無遺漏）與 AC-5.6（就地刪除不重抓）在 offset 分頁下確實會互相牴觸（developer 實測指出：刪一列後下一頁仍由原 offset 起算，會靜默略過一個帳號）。處置為「AC 兩條都保留、把衝突與其緩解手段記入 Assumptions 並指派 application-design 選定分頁策略」，而非在本階段改寫任一條 AC —— 選定緩解手段是設計決定（承 `cid:feasibility:c6` 的既有 correction），本階段記載風險與方向、不預選手段。此判斷是否足夠，交 reviewer 裁決。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-09T04:30:00Z — reviewer iteration 2 的 Finding A（Major，不阻擋 READY）：NFR-7 的**桌面**回歸驗證在 US-3 併入 US-1 的過程中失去 AC 落點，只剩小螢幕情境（US-4 AC-4.3）。主要 persona 的主要使用情境正是桌面。READY 後不回改（會使 review receipt 失效且 iteration 已用罄），已於 gate 向使用者明確揭露，由其決定是否 Request Changes；若不修正，須於 delivery-planning 或測試計畫補上落點。
- 2026-08-09T04:30:00Z — 另三項 Minor 未處理：US-1 未揭露首次引入 TestClient 樣板的一次性成本；design 的判斷類 OBJECT（Platform_Admin 在 0–90 天區間需自行心算日期差的體驗代價）既未裁決也未記載；WebSocket 活動是否計入最後活動時間未登錄為 assumption。
- 2026-08-09T04:30:00Z — 結構性教訓：故事合併（Q4=A 把 US-3 併入 US-1）時，被併故事的 AC 需逐條確認去向，否則其獨有的覆蓋會靜默消失 —— Finding A 正是此類遺漏（原 AC-3.2 涵蓋桌面既有操作不退化，合併後無人承接）。
- 2026-08-09T04:00:00Z — design 指出無紀錄態的候選 tooltip 文案若提及「上線前」，對上線後從未登入的新帳號並不成立；此約束已寫入 stories 的 assumptions，refined-mockups 定案文案時須滿足。
- 2026-08-09T04:00:00Z — AC-2.5 只確立「兩個破折號必須可區分」，具體視覺手段留 refined-mockups；區分不足會讓待審核帳號出現兩個外觀相同、語意不同、可及性不同的符號並排。
- 2026-08-11T00:00:00Z — mob 指出「只有一頁時分頁控制是否呈現」與「第一頁的上一頁該停用或隱藏」皆為線框明列的未定案項，而 DoD 的 e2e 斷言若預設「控制項恆可見」，會在實作正確（選擇隱藏）時紅燈。已把 AC-5.7 收斂為「兩種佈局採同一種處置」並在 Assumptions 記明不預選，但**單頁情境的 e2e 斷言究竟怎麼寫，仍取決於 OQ-7 的定案**，本階段無法給出確定文字。
- 2026-08-11T00:00:00Z — 型別契約同步（requirements C-9）無行為 AC 落點，改列 DoD。這是誠實的處置，但也意味著本 intent 最關鍵的一條編譯期護欄（`AdminPage.tsx` 的 `res.json()` → `DbUser[]` 使 `tsc -b` 對 envelope 變更完全無感）只由交付條件承載、不由驗收標準承載。若下游把 DoD 當成可協商項，這條護欄會第一個掉。
