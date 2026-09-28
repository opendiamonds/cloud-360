# Code Generation Questions — U-10a `ci.yml` 的回寫排除

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-10a-ci-writeback-exclusion · kind: packaging -->

## 上游前提推翻的裁決（已於計畫前取得）

**Question**: 已核可設計的一半（`concurrency` 加 `github.actor` 以區分機器與人）實測不成立——同步憑證為擁有者帳號 token，與開發者的 `github.actor` 同為 `opendiamonds`。[US:S-1 AC 7] 的「既有 run 不被取消」在 `pull_request` 事件下結構性無解。四個方向？

- **接受 PR 側會被取消** — push 側 `paths-ignore`（run 不建立）＋ PR 側前置 gate job（四個 job 全 skip）；AC 7 需回頭改寫
- PR 分組加 commit SHA — (a) 成立但廢掉 PR 節流，改變既有行為
- 另鑄機器帳號 token — 原方案成立但推翻 ADR-0016 的身分定案
- 同步不推有 PR 的分支 — 問題根源消失但推翻 U-4／U-6 已核可設計

[Answer]: 接受 PR 側會被取消 <!-- 2026-09-05T04:36:23Z, via AskUserQuestion -->

## Plan Approval

**Question**: `code-generation-plan.md` 已就緒（7 步驟；含兩項送裁決的介面判斷：gate job 在 `pull_request` 事件下須以 `github.event.pull_request.head.sha` 取 commit 訊息而非 HEAD（merge ref 的 HEAD 是合併結果、訊息不對）、靜態檢查腳本本輪不接進 `ci.yml`（會形成 `ci.yml` 檢查自己的循環，正確落點在 Bolt 1 整合驗證））。是否核可此計畫並開始產生程式碼？

- **Approve Plan** — 依計畫開始產生程式碼（含上述兩項介面判斷照計畫落地）
- **Request Changes** — 修訂計畫（請說明要改哪裡）

[Answer]: Approve Plan <!-- 2026-09-05T04:38:42Z, via AskUserQuestion -->
