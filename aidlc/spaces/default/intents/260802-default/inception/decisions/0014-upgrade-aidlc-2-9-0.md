# ADR 0014: 升級 AI-DLC v2 框架至 2.9.0

- Status: Accepted
- Date: 2026-09-20
- Related: ADR-0011（採用 AI-DLC v2）、ADR-0013（升級 AI-DLC 至 2.7.0）、`.claude/README-cloud360.md`、upstream [`CHANGELOG.md`](https://github.com/awslabs/aidlc-workflows/blob/v2.9.0/CHANGELOG.md)

### Context

本 repo 的 AI-DLC runtime 停在 2.7.0。upstream 於 2026-09-15 發布 2.9.0 stable，`v2` 分支最新 stable tag 亦為 `v2.9.0`；`v2.9.1-preview.20260915.1` 為 preview，不作為本 repo 的共享 runtime 基準。

2.7.0 至 2.9.0 的主要變更包括：

1. Classic scope 的新建 intent 改為 18-stage v1 flow，走到 Build and Test 即止；需要舊 Classic 圖（含 CI Pipeline 與 Operation）時改用 `workshop` scope。既有 in-flight Classic intent 保留其記錄圖。
2. Ceremony 設定改由 scope 擁有，`aidlc engine config set` 以 transaction 方式處理 depth、testing、review、change-control 與 ceremony。standalone `aidlc-utility.ts change-control` route 已移除，未知 `config-change` flags 會失敗。
3. 新增 `aidlc engine orchestrate wait`；record-level engine 檔移到 `<record>/.aidlc-engine/`，舊路徑仍可 fallback 讀取。
4. 新增 `/aidlc intent archive|unarchive`、`intent list --all`。
5. 新增 `aidlc attest resolve|anchor`，把 commit 或 diff range 對應到 reviewed Units。2.9.0 前的 review 無 committed source evidence，會回 `unverifiable`，直到下一次 per-Unit review。
6. Release packaging 分離 native runtime 與 Bun-based copy runtime；manual-copy 使用者應以 `aidlc-copy-runtime-2.9.0.tar.gz` 的 `runtime/<harness>/` 更新。

本 repo 在 `.claude/` 下有三處本地調整（見 `.claude/README-cloud360.md`），升級時必須保留：共享 `settings.json` 不帶 Bedrock/AWS/model 預設、`ai-dlc-principles.md` 的 v2 artifact 路徑修正、`tcms` stage 與 `/tcms-verify` skill。

### Decision

1. **升級至 upstream stable 2.9.0**，不採用 preview tag。從 upstream `v2.9.0` source tag 執行 `bun scripts/package.ts claude` 產生 `dist/claude/.claude/`，再整棵替換本 repo 的 `.claude/` runtime。
2. **保留 Cloud-360 三處本地調整**：
   - `settings.json` 採用新版 hooks/statusLine/permissions/companyAnnouncements，但 `env` 維持空物件，且不寫入 `model` 或 `effortLevel`。
   - `knowledge/aidlc-shared/ai-dlc-principles.md` 第 3 條仍指向 `aidlc/spaces/<space>/intents/<record>/`，因 upstream 2.9.0 仍保留舊 `aidlc-docs/` 文字。
   - 放回 `.claude/aidlc-common/stages/construction/tcms-test-cases.md` 與 `.claude/skills/tcms-verify/SKILL.md`，並重新產生 graph 與 runner。
3. **接受 Classic scope 行為變更**。本 repo 已在 ADR-0013 接受隱含預設 scope 為 `classic`，此處進一步接受 2.9.0 的 Classic 18-stage v1 flow；需要舊 Classic 圖時明示 `--scope workshop`。
4. **不遷移既有歷史 review evidence**。2.9.0 前 review 在 `aidlc attest resolve` 中可能顯示 `unverifiable`，這是 upstream 對舊 review 的預期結果；後續 per-Unit review 會自然補上新 evidence。

### Consequences

- **正面**：取得 intent archive/unarchive、attest resolve/anchor、bounded wait、record-level `.aidlc-engine/`、ceremony transaction 與 2.9.0 的 Construction autonomy 改進。
- **須知**：
  - 新建 Classic intent 的 stage graph 比 2.7.0 短；需要 CI Pipeline 或 Operation 時不要依賴 Classic，改用 `workshop` 或明確 scope。
  - 舊腳本若直接呼叫 `aidlc-utility.ts change-control` 或帶未知 `config-change` flag，升級後會失敗。
  - 2.9.0 前已完成的 review 對 `aidlc attest resolve` 可能是 `unverifiable`，不是資料遺失。
  - 每次後續升級仍需重放 `.claude/README-cloud360.md` 的三項 Cloud-360 調整。

### Verification

升級 PR 必須至少通過：

1. `bun .claude/tools/aidlc.ts --version`
2. `bun .claude/tools/aidlc-graph.ts compile`
3. `bun .claude/tools/aidlc-runner-gen.ts write`
4. `bun .claude/tools/aidlc-graph.ts compile --check`
5. `bun .claude/tools/aidlc-runner-gen.ts check`
6. `bun .claude/tools/aidlc-utility.ts plugin-sync`
7. `/aidlc --doctor` 或等價 `bun .claude/tools/aidlc.ts --doctor`
8. `python3 scripts/validate_repo_contract.py`

### Alternatives

- **停留在 2.7.0**：少了 archive/attest/wait 與 2.9.0 的 release/runtime 分離修正，且後續升級差距會繼續擴大。不採。
- **升級到 preview 2.9.1**：preview tag 不是 stable baseline，不適合作為本 repo 共享 runtime。不採。
- **只覆蓋 changed files，不做整棵 runtime 替換**：容易留下被 upstream 移除的 scopes、runner 或 hook，`README-cloud360.md` 已記錄 merge-copy 殘留風險。不採。
