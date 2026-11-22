# ADR 0023: 升級 AI-DLC v2 框架至 2.11.0

- Status: Accepted
- Date: 2026-10-19
- Related: ADR-0011（採用 AI-DLC v2）、ADR-0013（升級至 2.7.0）、ADR-0014（升級至 2.9.0）、`.claude/README-cloud360.md`、upstream [`CHANGELOG.md`](https://github.com/awslabs/aidlc-workflows/blob/main/CHANGELOG.md)

### Context

本 repo 的 AI-DLC runtime 停在 2.9.0（copy-channel：hook 與工具經 `bun .claude/tools/*.ts` 執行）。intent `260920-orchestration-brain` 的 code-generation 在 2.9.0 下陷入無法自行脫離的狀態：單元 `object-picker-ui` 的補救額度用完後，引擎只開放「Request Changes」一條路，但三種送出方式（選單選擇、直接輸入、選單後輸入）都被拒絕，且拒絕訊息未說明原因；同時 plan-approval-guard 擋下幾乎所有 shell 指令，連 `--doctor` 都無法由 agent 執行。

2.9.0 → 2.11.0 的 upstream 變更中與此直接相關者：

1. **2.11.0**：引擎自行提出 Plan Approval 並追蹤計畫指紋，同一份計畫只問一次；審查未完成時可在關卡以「Approved. The <Stage> review did not finish.」核可；Guard Policy 除 `enterprise` 外預設 `off`。
2. **2.10.0**：復原訊息一律指出可執行的下一步；Construction 審查改在已驗證的 Unit 與批次檢查點進行。
3. **升級方式**：`aidlc update` 安裝 native 執行檔，`aidlc config --yes` 刷新專案檔；進行中的工作可接續（「Open work carries on through the refresh」），無 state 版本變更、無 hook 更名。

### Decision

1. **升級至 2.11.0，並由 copy-channel 改為 native 執行檔**：`aidlc update` 後執行 `aidlc config --yes --force`。因本專案原為複製安裝，`config` 視 `.claude/` 全部 154 個檔為「本機改過或不屬於我」而停下；覆蓋前已確認 `.claude/` 無未 commit 改動，任何被覆蓋的內容皆可由 git 還原，故採 `--force`。
2. **保留 Cloud-360 三處本地調整**：
   - `settings.json`：採用新版的權限、hook 與 statusLine，但移除新版加回的 `env.AWS_AIDLC_DEFAULT_SCOPE`，`env` 維持空物件。Bedrock／model 相關鍵新版未加回。
   - `knowledge/aidlc-shared/ai-dlc-principles.md` 第 3 條：重新套用 v2 record 路徑修正（upstream 2.11.0 仍為 `aidlc-docs/`）。
   - `tcms-test-cases` stage 與 `tcms-verify` skill：升級未覆蓋，原樣保留。
3. **2.11.0 起，`.claude/settings.json` 與 runtime 檔視為安裝檔**：agent 在工作流程中不得修改，只能經官方更新程式或人在外部終端機修改。
4. **接受升級寫入 `.gitignore` 的 `AI-DLC:gitignore` 區塊**（upstream 2.11.0 改為單一區塊、置於團隊自有規則之後）。

### Consequences

- **正面**：取得 2.11.0 的 Plan Approval 自管、審查未完成仍可核可、Guard Policy 預設放寬、以及 2.10.0 的可執行復原訊息。
- **新揭露的事實**：2.11.0 對同一個復原狀態明白標出，code-generation 在 unit-major 下送出 Request Changes 會**作廢全部單元**已完成的 code-generation 成果。2.9.0 的三次拒絕因此避免了 24 個單元的重做。此後不得以 stage 級退回修改處理單一單元的修正。
- **未解決**：升級後該復原問題仍只剩 Request Changes 一個選項，且問題開啟期間 agent 的所有檔案寫入（含 session scratchpad）皆被拒絕。另案回報上游。
- **須知**：
  - `aidlc doctor` 會持續顯示「AI-DLC files: 1 changed」指向 `ai-dlc-principles.md`；這是客製被辨識的證據。日後執行 `aidlc config` **不得**加 `--force`，否則客製會被覆蓋。
  - `tcms` 仍未整理成正式 plugin root，doctor 的「Plugins: 1 need attention」為既知 advisory，**不得**執行 `aidlc engine plugin sync --prune-missing`。
  - `aidlc engine testing-posture fingerprint --reapprove` 已退役。
  - 非 `enterprise` scope 的進行中 intent 改為只由主導 agent 處理，需要協作 agent 時輸入 `/aidlc --collaborators on`。
  - 升級後須完全重開 Claude Code，新 hook 才會生效。
  - 指令入口改為 `aidlc engine ...`；`bun .claude/tools/...` 的舊形式仍存在於歷史紀錄與記憶中，以新形式為準。

### Verification

本次升級實際執行並通過：

1. `aidlc engine runtime compile`
2. `aidlc doctor`：0 problems；warning 皆為既知或與升級無關
3. `python3 scripts/validate_repo_contract.py`：passed
4. `python3 scripts/validate_env_contract.py`：passed

### Alternatives

- **停留在 2.9.0**：code-generation 關卡無法脫離，且 Plan Approval 失效造成的死結已在本 intent 發生三次。不採。
- **只換 native 執行檔、不刷新 `.claude/`**：專案仍經 `bun .claude/tools/*` 執行 2.9.0 的引擎，修正不會生效。不採。
- **逐檔搬走衝突檔再執行不帶 `--force` 的 `config`**：154 個檔中真正的客製只有兩處，其餘皆為 upstream 原檔；逐檔處理成本高且無收益。不採。
