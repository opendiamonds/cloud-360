<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-24T00:21:54Z — 引擎算出的 codekb 路徑是 `codekb/chiton/`（由 worktree 目錄名 basename 推導），但 `project.md` 明文要求 codekb 寫進以 repo 命名的目錄。處置：在路徑解析類指令（`codekb`、`codekb-scope-diff`、`codekb-snapshot`、`codekb-publish`）帶 `--repo cloud-360`，但兩個 `aidlc-log.ts link` 收據**不帶** `--repo`——因為 `intents.json` 的本 intent 列沒有 `repos` 欄位，依 stage 檔屬「unrecorded project-root repo」，收據不得 repo-qualified。不以手改 `intents.json` 繞過（該做法會讓 swarm prepare 去找不存在的兄弟目錄）。
- 2026-09-24T00:43:44Z — **「Full rescan」是輸出取代的範圍，不是深度的宣稱**。使用者選 Full rescan，但實際深讀只有 33 個路徑（27 支 backend 模組僅取簽章、37 支測試檔一行沒讀、`backend/prompts/`／`lenses/` 未開啟），故 `kind` 誠實填 `partial` 且不含 `./`。若因為「使用者選了 full」就填 `kind: full`，等於告訴下一次 rerun guard 那些全部已驗證——而那是假的。兩件事必須分開判：breadth 由人選，depth 由實際讀了什麼決定。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-24T00:21:54Z — 守衛對 `cloud-360` 回 UNKNOWN_SCOPE（store 早於 scope 追蹤），依 stage 規則**不提供「沿用」選項**，只問 Full rescan vs Focused scan。出題前只取統計事實（commit 數、diffstat、檔案計數），未讀任何原始碼、未產生檔案清單——依 `project.md` 的 reverse-engineering conductor 界線。使用者選 Full rescan。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-24T00:43:44Z — 深度切分落在**檔案內部**時（`collab_router.py` 只讀 WS 區段 L245–300、`review_router.py` 只讀 SSE 區段、`design_agent.py` 只讀 L1–45），`analyzed.paths` 的粒度是檔案／目錄、表達不了行區間。處置是把該元件留在淺掃區、不進 `analyzed.components`，只在內文對真的讀過的幾行標 `[讀]`，並在 artifact 內寫明這個選擇的理由——寧可低報覆蓋，不可讓 guard 之後把整支檔當成已驗證。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-24T00:21:54Z — **`orchestrate wait --stage reverse-engineering --for artifacts` 在本站不是可用的等待訊號**：它回 `settled` 且 `missing: []`，但 link 1 的 handoff（`developer-scan.md`）根本還沒寫出來。原因推測是 codekb 是跨 intent 共用的 space-level store，上一個 intent 留下的 9 份舊 artifact 已經滿足它的存在性檢查。實務上要等的是 handoff 檔本身，不是 produces。待確認這是工具的預期行為還是本站特有的落差。
- 2026-09-24T00:43:44Z — **coverage backstop 在本輪沒有提供任何保證**：`codekb-scope-diff --compare` 回 UNKNOWN_SCOPE（舊 store 無 scope 區塊可比），所以既沒有 COVERS 也沒有 NARROWER。stage 檔說「COVERS 或無 prior store 不需警告」，但本輪是第三種情況——有 store 卻無可比區塊，工具實際上什麼也沒驗。這一點必須在關卡上向使用者講明，不能因為「沒出現 NARROWER」就讓它看起來像通過了檢查。
- 2026-09-24T00:43:44Z — **`codekb/cloud/` 仍未收斂**（2026-08-06 的過期庫）。本輪確認 publish 正確落在 `codekb/cloud-360/`、未產生 `codekb/chiton/`，但三份庫變兩份的收斂本身沒有處理，也不在本 stage 的職責內。
