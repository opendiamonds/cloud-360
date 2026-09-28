<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-23T15:01:55Z — 依 approval-handoff Q3=A 把本 stage 界定為**兩區定向掃描**（Area 1：AI-DLC 狀態表徵；Area 2：gh-aw workflow 語料），其餘七成內容不重新推導、只逐節加新鮮度標註；並在 `reverse-engineering-timestamp.md` 立四級標記（［本輪重寫］／［本輪機械複驗］／［差異標註］／［沿用 `c3de2c8`］），讓下游能分辨每一節的可信度而不是把整份 codekb 當同一新鮮度。
- 2026-08-23T15:01:55Z — 差異標註再細分兩級證據強度（「已讀 diff」vs「僅 diffstat」）並逐檔列名；理由是 diffstat 推得的一行級描述若與實讀 diff 混列，下游無從分辨哪些是核對過的事實。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-23T15:01:55Z — **未寫入 `codekb-path` 印出的 `aidlc/spaces/default/codekb/chiton/`，改就地更新 `codekb/cloud-360/`**。stage 檔明文要求「verbatim 寫入工具印出的目錄，不得以手組路徑取代」，但該路徑由 `basename(projectDir)` 推導、本 clone 目錄名為 `chiton`，照做會為**同一個 repo** 開出第三份 codekb（現已有 `cloud-360/` 3,000+ 行與過期的 `cloud/` 582 行）。引擎的完成檢查對 `codekb/*/` 做 ANY-exists 判定，寫進 `cloud-360/` 即滿足。
- 2026-08-23T15:01:55Z — 刻意不改 `intents.json` 補 repo 名來繞開上一條：一旦寫入 repo 名，swarm `prepare` 會去找一個不存在的同名兄弟目錄。
- 2026-08-23T15:01:55Z — link 2（architect）額外讀入 `0012-github-issues-projects-wiki-sync.md` 與 `0013-aidlc-projects-sync-scoping.md` 兩份 ADR，超出 link 1 的掃描邊界；理由是它們是本 intent 的直接前案，已落入 `architecture.md` 的「開發流程層架構」。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-23T15:01:55Z — 以「兩區重掃＋逐節新鮮度標註」取代全 repo 重掃：代價是其餘七成內容的實際新鮮度仍停在 `c3de2c8`（2026-08-17），且未指出的過期點不代表沒過期；換得的是本 intent 真正需要的兩區語料在 `9307dbc` 上是實掃結果。全 repo 重掃已被提出並在 Q3 明確否決。
- 2026-08-23T15:01:55Z — 測試與 lint 數字採靜態計數（grep／解析 `openapi.json`）而非實際執行：未跑 `unittest`、Playwright、`docker build`、兩支 validator 與 `eslint`；換得掃描成本可控，代價是前一基準的「0 errors, 3 warnings」與 validator「passed」本輪未複驗。

## Open questions
- 2026-08-23T06:48:13Z — **阻塞級發現**：ADR-0012「AI-DLC 與 GitHub Issues／Projects／Wiki 的雙向同步」（Accepted，2026-08-16，182 行）涵蓋本 intent 的主題，但整個 IDEATION 四站無一引用。與已核可決定有六處衝突，四處為直接矛盾：①映射層級（ADR：intent→一整個 Project、story→Issue；本 intent：intent→Project #16 的一則 issue）②反向同步（ADR 列為階段 2 且狀態真實來源在 GitHub；本 intent 列入 Won't Have）③承載形式（ADR 指定 scripts/aidlc_sync_*.py；使用者本 session 新增的規則禁止 repo 內程式）④階段順序（ADR 明文 Projects 為階段 3 且階段 1 未完成前不啟用階段 2；本 intent 直接做 Projects）。另 ADR 的技術前提已過期（它記載 gh-aw safe-outputs 無 Projects 操作，但本 intent 查證確認 update-project 存在），且其 Alternatives 段明文否決的方案 A（repo 永遠贏、GitHub 純鏡像）實質即本 intent 的設計。已暫停 reverse-engineering 並交付使用者裁決。
- 2026-08-23T06:48:13Z — 未查 decisions/ 是本輪的方法缺口：feasibility 的唯讀查證涵蓋了 workflows、gh-aw 官方文件、GitHub API 與 repo 現況，唯獨沒查既有 ADR。ADR 是本專案架構級決策的正式落點（project.md 明載），主題重疊的 intent 未查 ADR 等於在未知的既有決定上做設計。
- 2026-08-23T06:48:13Z — 次要發現：codekb 已有同一個 repo 的兩份知識庫（codekb/cloud-360 共 3087 行、基準 commit c3de2c8／2026-08-17；codekb/cloud 共 582 行），而 codekb-path 以工作目錄名決定 repo 名，故本次會寫出第三份 codekb/chiton。HEAD 距該基準 20 個 commit、71 個檔案。是否重掃、寫哪裡，待前述裁決後一併處理。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-23T15:01:55Z — 前三條 open question 的處置結果：①②（ADR-0012 衝突）已由 **ADR-0013『aidlc-projects-sync-scoping』（Accepted 2026-08-23）** 裁決收斂，ADR-0012 的 Status 行已加註修訂指標，兩者須併讀；③（codekb 寫哪裡）已由上方 Deviations 的裁定處理。**但「兩份（潛在三份）codekb 如何收斂」本身仍未定案。**
- 2026-08-23T15:01:55Z — **本 codekb 的基準 `9307dbc` 已落後 `origin/ut`（現為 `be73385`）三個 commit**，其中兩項直接影響結論：PR #532 把 gh-aw 由 `v0.81.6` 升到 `v0.86.2`（Area 2 的每一項版本事實只對 `9307dbc` 成立，尤其 `timeout-minutes` 被靜默丟棄那條是對 v0.81.6 的實測、未在 v0.86.2 複驗）、PR #508 把 `scripts/` 由 4 支增為 7 支。下一輪 reverse-engineering 應以 `ut` 為基準。
- 2026-08-23T15:01:55Z — **待裁定的規則衝突**：ADR-0013 把 `scripts/aidlc_sync_*.py` 從設計中移除，且 `project.md ## Forbidden` 於 2026-08-23 新增「不得以 repo 內**新增**的實作程式承載流程自動化與外部系統同步」；而 PR #508 已於 2026-08-22（規則生效前一天）把這三支腳本合併進 `ut`。「既有豁免／遷移到 gh-aw／收窄規則」三者需要一個明確決定。本 stage 只記載、不裁定。
- 2026-08-23T15:01:55Z — 本 stage 的未讀清單是真實邊界，下游不得假設已涵蓋：11 個 `.lock.yml` 無一全讀（agent job 內部的 prompt 組裝、firewall、MCP 啟動、safe-output 收集腳本一行未看）、`aidlc-state.ts`（3,503 行）未通讀、audit shard 各事件型別的欄位未盤點、`backend/services/` 與 `frontend/src/pages/` 其餘模組未掃、執行期行為完全未觀察。
