# ADR 0013: 升級 AI-DLC v2 框架至 2.7.0

- Status: Accepted
- Date: 2026-09-06
- Related: ADR-0011（採用 AI-DLC v2）、ADR-0006（採用 AIDLC 框架）、`.claude/README-cloud360.md`、upstream [`CHANGELOG.md`](https://github.com/awslabs/aidlc-workflows/blob/v2.7.0/CHANGELOG.md)

### Context

本 repo 自 ADR-0011 起以 AI-DLC v2 為唯一的 AI-SDLC 框架，安裝版本停在 2.5.33（commit `f17c40f`）。upstream 於 2026-09-01 發布 2.7.0，把整個 2.6.x 週期（2.6.1 至 2.6.124，共 124 個 patch）收斂成新的 minor baseline。2.5.33 與 2.7.0 之間累積的變更，對本專案有實際影響的有六項：

1. **Inception 設計階段重組（2.6.1）**：`application-design` 更名為 `domain-design`，新增 CONDITIONAL 的 `contract-design`，`delivery-planning` 由 2.8 移到 2.9；functional-design 與 infrastructure-design 的產出檔名整併。基礎 stage 數由 32 變 33。**持久化的 state schema 升為 v8**，v7 的 `aidlc-state.md` 會被 `/aidlc --doctor` 與 `next`／`report` 明確拒絕，upstream 不提供遷移工具。
2. **預設 scope 改為 `classic`（2.6.18）**：未指名 scope 且關鍵字未命中時，隱含預設由 `feature`（完整生命週期）改為 `classic`（v1 式、無 Ideation）。新增 `express` scope。`settings.json` 的 `AWS_AIDLC_DEFAULT_SCOPE` upstream 預設值由 `workshop` 改為 `classic`。
3. **Hook 檔案更名與新增**：`aidlc-mint-presence.ts` → `aidlc-record-human-turn.ts`、`aidlc-audit-logger.ts` → `aidlc-write-audit-log.ts`、`aidlc-sensor-fire.ts` → `aidlc-run-sensors.ts`、`aidlc-dispatch-rules.ts` → `aidlc-deliver-stage-rules.ts`；新增 `aidlc-fold-usage.ts`（token 用量）、`aidlc-plan-approval-guard.ts`、`aidlc-review-freeze.ts`、`aidlc-continue-workflow.ts` 等。Claude Code 使用者升級後必須經 `/hooks` 重新核准專案 hooks 並完整重啟。
4. **Reviewer stage 必須宣告 `review_artifact:`（2.6.121）**：自訂或 plugin stage 若有 `reviewer:`，編譯會拒絕未補 `review_artifact:` 者。
5. **Plugin 工具鏈（2.6.110 起）**：引擎重裝會還原 stock graph，每次升級後必須跑 `plugin sync`。
6. **DocumentKB（2.6.15）**：新增 `knowledge/documents/`（使用者擁有）與 `knowledge/documentkb/`（工具擁有）的文件目錄，並有新的 `.gitignore` 項目。

本 repo 在 `.claude/` 之下有三處自有調整（`README-cloud360.md`），升級的整批複製會把它們覆蓋，必須逐項放回。

### Decision

1. **升級至 2.7.0**，以 upstream `dist/claude/` 整棵取代 `.claude/`，`AIDLC_VERSION` 為 `2.7.0`。刪除 merge copy 會殘留的舊 runner `skills/aidlc-application-design/` 與已移除的 hooks。
2. **三處自有調整逐項放回**（見 `README-cloud360.md`）：
   - 調整 1：`settings.json` 的 `env` 維持空物件。upstream 新增的 `AWS_AIDLC_DEFAULT_SCOPE=classic` 一併不進版控——引擎的硬編碼 fallback 本來就是 `classic`，寫與不寫行為相同，維持「環境相依鍵不進共享設定」的原則。**接受隱含預設由 `feature` 變為 `classic`**：本專案的 intent 一律以描述觸發 scope 自動偵測，實務上不依賴隱含預設；需要完整生命週期時明示 `--scope feature`。
   - 調整 2：`ai-dlc-principles.md` 第 3 條的 `aidlc-docs/` 路徑重新改為 record 目錄（upstream 2.7.0 仍未修）。
   - 調整 3：放回 `tcms-test-cases.md` stage 與 `tcms-verify` skill，重跑 `aidlc-graph.ts compile` 與 `aidlc-runner-gen.ts write`。tcms stage 無 `reviewer:`，不受第 4 項影響。升級後 graph 為 34 stages（aidlc 30、bootstrap 3、tcms 1）。
3. **既有 v7 state 的 intent 不做手工遷移**。五個帶 `aidlc-state.md` 的 intent 均為 State Version 7：`drawio-templates`、`production-path-check` 已完成，不需再推進；`default`（baseline record）、`last-login-column`（停在 feedback-optimization）、`a1-a3-ux`（停在 build-and-test）登記為 in-flight，但實際工作已合併至 `ut`。這三者的 record 完整保留作為歷史紀錄；若日後需要在新 shell 上繼續其中任一個，開新 intent 並引用舊 record，不改寫引擎擁有的 state 檔。
4. **規則層同步更名**：`project.md` `## Mandated` 中 Cursor harness 的 HUMAN_TURN 補寫規則，hook 路徑由 `aidlc-mint-presence.ts` 改為 `aidlc-record-human-turn.ts`，並註明版本對應。歷史 stage diary 中的舊檔名不改。
5. **`.gitignore` 補上 upstream 新增項目**：`aidlc/spaces/*/intents/.aidlc-*`（pre-intent hooks-health scratch；先前四個 `.last` 心跳檔被誤納入版控，本次 `git rm --cached`）、`aidlc/spaces/*/knowledge/documentkb/.journal/`、`aidlc/spaces/*/knowledge/.sources.local.json`。
6. **升級後驗證全部通過**：`aidlc-graph.ts compile --check`、`aidlc-runner-gen.ts check`、`/aidlc --doctor`（50 passed, 0 failed）、`plugin-sync`（exit 0）、`validate_repo_contract.py`、`validate_env_contract.py`。CodeKB scope timestamp 無 2.6.x 修復前的空樹 fingerprint。

### Consequences

- **正面**：取得 Domain／Contract Design 對實作單元邊界的強化、Testing Posture 帶入 Code Generation、有界的 Build and Test 回圈、reviewer 收據綁定 artifact 與 source 狀態、token 用量統計、DocumentKB 文件輸入、Classic／Express 兩個較短路徑。後續升級可依 upstream 的 minor baseline 節奏進行，不再需要追 patch。
- **負面／須知**：
  - 三個 in-flight 的 v7 intent 在新 shell 上無法 `--resume`；若切換 active-intent 到它們，`/aidlc --doctor` 會紅燈。這是接受的代價，不是缺陷。
  - 隱含預設 scope 變為 `classic`；未帶關鍵字的模糊描述會走無 Ideation 的路徑。需要完整 Ideation 時明示 scope。
  - 每位開發者拉到此變更後必須 `/hooks` 重新核准並完整重啟 Claude Code；Cursor 使用者的 HUMAN_TURN 補寫指令換了檔名。
  - `.claude/CLAUDE.md`（upstream 檔）仍描述「shipped `settings.json` 走 Bedrock」與 `docs/guide/` 等本 repo 不存在的路徑，與 ADR-0011 時期相同，不修 upstream 檔。
- **升級 checklist 更新**：`README-cloud360.md` 的「重新安裝或升級時」補上四個本次實測發現的步驟——跑 `plugin-sync`、檢查 state version、grep 規則層引用的 hook 檔名、比對 upstream `.gitignore` 新增項。

### Alternatives

- **停留在 2.5.33**：upstream 已把 2.5.x 視為停止維護的舊 shell（2.7.0 release note 要求「finish and archive every workflow created before 2.6.1」）。愈晚升級，累積的 breaking change 愈多，且 2.6.121 的 reviewer 收據綁定等安全性改進拿不到。不採。
- **在 `settings.json` 寫入 `AWS_AIDLC_DEFAULT_SCOPE=feature` 保留舊的隱含預設**：違反調整 1 的原則（環境相依鍵不進共享設定），且本專案實務上以描述觸發偵測，隱含預設極少被命中。改為在 ADR 明文接受 `classic`，需要時明示 scope。不採。
- **手工把 v7 state 改寫為 v8**（把 `application-design` 列改名、插入 `contract-design` 列、bump State Version）：state 檔為引擎擁有，upstream 明言「no user-visible migration」，手改後 audit shard 與 state 的一致性無從驗證，且三個 in-flight intent 的實際工作已合併，沒有推進需求。不採。
- **把 tcms stage 改成正式 plugin root（`hooks/compose.ts`）以走 `plugin sync`**：2.7.0 的 plugin 工具鏈已成熟，這是合理方向，但屬獨立工作，不與版本升級夾帶。留待後續 intent。
