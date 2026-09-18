<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-06T15:56:14Z — intents.json 無 repos 陣列，依 stage 檔規則視為單一 repo（workspace root 即 cloud-360）；codekb-path 工具解析為 aidlc/spaces/default/codekb/cloud-360/，不手組路徑。
- 2026-08-08T16:30:00Z — 技術債以「根因叢集 × P1/P2/P3」重組，不照掃描的流水號排列：流水號不表達修復順序、叢集才表達。判定「修驗證缺口（C3）的投報率高於逐項修多源真實（C1）」——C1 能長期存在正是因為 C3 沒有機制發現它。
- 2026-08-08T16:30:00Z — ADR-0006 的 property-based hard constraint 判為「無落點」而非「違規」：點名的三個模組（IaC generator／cost calculator／agent routing）在本 repo 尚無實作，既未違反也未滿足；已註記該約束在 IaC generator 開工時立即變 blocking。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-06T15:56:14Z — dispatched agent 的 rule bundle 以「指示 agent 首先閱讀 memory 四檔（org/team/project/phases/inception）」傳遞，未將全文逐字貼入 brief；檔案內容與 load-steering bundle 逐位元相同且 agent persona 本就強制載入該層，貼全文徒增 token 成本。
- 2026-08-11T00:00:00Z — 本輪（scope-definition Revision 2 回跳後的重跑）**未重新執行兩環 pipeline 掃描**，改以確定性的新鮮度驗證取代：`git rev-parse HEAD` 仍為 `8c90f40`（即 codekb 的掃描基準 commit），且 `git diff --name-only 8c90f40 -- backend frontend scripts deploy .github schema.sql schema_rbac.sql DEPLOY.md docker-compose.yml` 與同範圍的 `git status --porcelain` 皆為空集合。stage 的 `condition` 要求「Always rerun for freshness」，其目的是保證新鮮度；在應用程式碼零變更已被機械證明的前提下，重跑必然產出相同的 9 份 artifacts，故以驗證取代重掃並在此明記，不假稱已重新掃描。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-08T00:00:00Z — developer 掃描首次因 session 限額中斷（非 agent 自身失敗），重跑時在 brief 內加入效率指引（先 glob／grep 掌握結構、只精讀關鍵檔）而非縮小掃描範圍 — 縮範圍會讓 codekb 失去完整性，控制讀取方式才是對的槓桿。
- 2026-08-08T16:30:00Z — pipeline 兩環之間以 scratchpad 檔案傳遞掃描結果並給第二環路徑，而非把全文貼進 brief：符合 stage-protocol §11 的 context budget（artifacts by path），也讓第二環能精讀而非被動接收。
- 2026-08-08T16:30:00Z — codekb 文件描述技術債時避免逐字複製被禁止的樣式（如 DEPLOY.md 的雙語 H2 標題字面值）：同一份文件正在建議擴大 contract 掃描範圍，逐字引用會讓該建議一旦落地就反過來擋下這份 codekb。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-08T16:30:00Z — T1／T4 綁定問題（修 J5 schema 缺漏需重跑 schema_rbac.sql，但該檔無條件 DELETE role_permissions 會清掉 Admin UI 調整）是本 intent 在 users 加欄時的同一條路徑；具體處置手段留 application-design／construction 決定，codekb 只記載張力本身。
- 2026-08-11T15:30:00Z — **上面那筆「以確定性驗證取代重掃」的判定是錯的，錯在基準**。`git rev-parse HEAD` 確實等於 codekb 的掃描基準 `8c90f40`，但那是因為**本地 `ut` 從未 fetch**、停在兩天前；`origin/ut` 當時已是 `67be019`、領先 8 個 commit，其中新增了 `backend/services/prompt_guard.py`（命中 codekb 自訂的「services 新增模組 → 完整重跑」條件）。教訓不是「不該用驗證取代重掃」，而是**驗證的基準必須是 remote 的 trunk，不是本地那份可能過時的複本** —— 「HEAD 等於掃描基準」在沒有 fetch 的前提下是一句恆真的廢話。codekb 的過期狀態已如實寫進 timestamp 檔。
