<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-09T02:00:00Z — 出題聚焦在 ideation 明列為「留待 requirements-analysis 定案」的三項（N 值、保存上限與清除語意、寫入頻率緩解手段的約束邊界），以及 practices-discovery 的 evidence.md 傳下來、會影響需求正確性的既有實作事實；上游已定案項目（欄位語意、空值呈現、時間格式、標示形式、可見角色、測試底線）一律不重問。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-09T02:10:00Z — reviewer iteration 1 判 NOT-READY（1 Critical＋3 Major＋2 Minor），六項全數採納修正後 iteration 2 判 READY。Critical 為本 stage 的實質錯誤：問題檔前言的「已由上游定案」清單憑 feasibility 的粗略措辭寫成「空值顯示『無紀錄』」，未回頭核對 rough-mockups 已核可的破折號決策，使 FR-2.3／NFR-6 與唯一已核可的視覺設計直接矛盾。

- 2026-08-11T00:00:00Z — Revision 1（PU-6 分頁）以 Modify 模式疊加：Q1〜Q5 的題幹／選項／答案與 FR-1〜FR-5、NFR-1〜NFR-7、C-1〜C-8 一律不動，只新增分頁的行為契約。reviewer iteration 1 判 NOT-READY，Critical 為本輪的實質錯誤：C-10 與 Q6 前言把「角色調整」與「啟停用」合併宣稱為「既有皆不重抓清單」，而 `AdminPage.tsx:113`／`:129` 實為 `fetchUsers()` 整份重抓 —— 與 `project.md` 已記載的 `cid:rough-mockups:rev1-c1`（把實作副作用誤植為既定事實並讓錯誤前提支撐整條論證鏈）同型，且我在出題前**確實讀過該檔**卻仍寫錯，問題不在沒查而在查了沒逐行核對。iteration 2 驗證輪判 READY。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-09T02:10:00Z — 修正 Critical 時把 FR-2.3 與 FR-2.4 的職責切開（FR-2.3 只定義「無資料不套逾期標示」的語意判定，FR-2.4 獨佔呈現形式），而非把兩者合併：同一個 UI 元素的外觀只該由一條需求宣告，語意與呈現分屬不同的變更理由。
- 2026-08-09T02:10:00Z — ADR-0006 四面向以「逐項判定表」呈現而非散在各處：hard constraint 要求四項缺一不可，表格讓「有沒有漏一項」成為可一眼核對的事實，散文式陳述則不可判。encryption 與 network exposure 判為不適用時一律附理由，不留空白。

- 2026-08-11T00:00:00Z — Q6 的更正走「只修理由不改決定」而非重開該題：三個選項的比較在更正後的事實下結論不變（A 仍是唯一保住逐帳號查驗工作流的選項），改動的只是「改動最小」這個理由對啟停用不成立。重開已答題會讓下游誤以為決定本身有變。
- 2026-08-11T00:00:00Z — 每頁筆數與 envelope 形式不在本站定案，即使「requirements 須可測試」會因此留下未定參數：已核可的 scope Revision 2 明文把它指派給 application-design，本站代決等於下游越權的鏡像。改以「升格為上線前置依賴」承接（沿用 FR-3.1 門檻 N 的同一形狀）。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-09T02:10:00Z — reviewer iteration 2 的三項新 Minor（FR-4.3 的 [raid:D1] 標籤冗餘、四面向表 Encryption 列無引用標籤、「範圍外」首段稱三類皆承自 scope-document 但第三類實為本階段新識別）READY 後不回改（會使 review receipt 失效且 iteration 已用罄），留待下游 stage 引用本檔時順手清理。
- 2026-08-11T00:00:00Z — iteration 2 驗證輪的三項新 Minor（[impl] 標籤未一致附行號、四面向表 Audit logging 列脫離語境會與 7 個 _audit_append 呼叫點字面衝突、FR-6.5 補充段重新開放了 Q6 已排除的 Option B）**已於 READY 後全數修正**，與 2026-08-09 那批「READY 後不回改」的處置不同：其中 Option B 一項會直接誤導實作（下游會以為兩種改法皆可），不屬純文字瑕疵。修正內容記於 artifact 的「Iteration 2 驗證輪後的收尾修正」表，不重開 reviewer。
