# Cloud-360 對 AI-DLC v2 安裝的調整

本目錄由 upstream [`awslabs/aidlc-workflows`](https://github.com/awslabs/aidlc-workflows) 的 `v2` 分支產出複製而來。除下列**三處**外，內容與 upstream 一致。

版本的單一事實來源是 `.claude/tools/aidlc-version.ts` 的 `AIDLC_VERSION`（跑 `/aidlc --version` 可查），目前為 **2.9.0**（ADR-0014）。升級歷程：2.5.11 並行安裝（upstream commit `257b43a`，見 commit `4f2b626`）→ 2.5.33（commit `f17c40f`，ADR-0011）→ 2.7.0（ADR-0013）→ 2.9.0。

## 調整 1：`settings.json` 移除環境相依設定

upstream 的 `settings.json` 是**進版控**的共享檔案，預設帶著 AWS workshop 情境的設定。原樣 commit 會強制本 repo 的每位開發者走 Bedrock，沒有 AWS 憑證者會直接失敗。

已移除下列項目：

| 項目 | upstream 預設 | 移除原因 |
|---|---|---|
| `CLAUDE_CODE_USE_BEDROCK` | `1` | 強制走 Bedrock；本團隊未必都使用 |
| `AWS_REGION` | `us-east-1` | 環境相依 |
| `ANTHROPIC_DEFAULT_*_MODEL` | `global.anthropic.*` | Bedrock 專用 model ID，非 Bedrock 環境無效 |
| `AWS_AIDLC_DEFAULT_SCOPE` | `classic`（2.6.18 前為 `workshop`） | 由 `/aidlc` 依描述自動偵測；未命中關鍵字時引擎的硬編碼 fallback 本來就是 `classic`，寫與不寫行為相同。隱含預設自 2.6.18 起由 `feature` 變為 `classic`，需要完整 Ideation 時明示 `--scope feature`（ADR-0013） |
| `model` | `opus[1m]` | 個人偏好 |
| `effortLevel` | `xhigh` | 個人偏好 |

`permissions`、`statusLine`、`hooks`、`companyAnnouncements` 均維持 upstream 原樣。

> ⚠️ 因此 upstream 的 `.claude/CLAUDE.md` 中「shipped `settings.json` 預設走 AWS Bedrock / Opus 4.8 / `AWS_REGION=us-east-1`」那段敘述**不適用於本 repo** — 那些鍵已被移除，`env` 為空物件。需要 Bedrock 的人請寫進自己的 `settings.local.json`。

## 調整 2：`knowledge/aidlc-shared/ai-dlc-principles.md` 的 artifacts 路徑

upstream 該檔第 3 條原則寫「Every stage produces versioned markdown documents in `aidlc-docs/`」—— 這是 v1 的扁平佈局，與 v2 自身的 per-intent record 設計矛盾（`aidlc-state.ts` 的註解明寫 `flat aidlc-docs/ root is gone`）。屬 upstream 未清乾淨的殘留。

已改為指向 `aidlc/spaces/<space>/intents/<record>/`。這是**純文件敘述**的修正，不影響任何程式行為。

> upstream 其他仍提及 `aidlc-docs` 的地方是**刻意**的，不要改：
> - `.claude/tools/aidlc-lib.ts` 的 `FLAT_MIGRATION_ROOT` — v1→v2 一次性搬遷的偵測常數
> - `.claude/sensors/*.md` 的 `matches: "**/{aidlc-docs,intents}/**"` — 同時匹配新舊佈局，讓 sensor 對兩種 repo 都會觸發
> - `.claude/knowledge/aidlc-shared/worktree-info-schema.md` — 描述 per-Bolt worktree 的 forked state 路徑

## 需要這些設定的人怎麼做

複製範本到 gitignored 的個人設定檔，各自填寫：

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

`settings.local.json` 已列入 `.gitignore`，優先權高於 `settings.json`，不會影響他人。

> ⚠️ upstream README 指出 v2 在 **Claude Opus 4.8** 上表現最佳；較弱的模型可能讓 conductor 跳過 reviewer pass 或 learnings ritual、草率通過 approval gate。若要固定模型，請寫在自己的 `settings.local.json`。

## 調整 3：新增 `tcms` plugin 的 `tcms-test-cases` stage

**這是新增檔案，不是修改 upstream 檔**，但它位於 `.claude/` 之下，因此同樣會被升級時的整批複製波及。

| 項目 | 路徑 | 性質 |
|---|---|---|
| Stage 檔（**手寫，需備份**） | `.claude/aidlc-common/stages/construction/tcms-test-cases.md` | 手寫來源 |
| 驗證 skill（**手寫，需備份**） | `.claude/skills/tcms-verify/SKILL.md` | 手寫來源，`/tcms-verify` |
| Runner skill | `.claude/skills/tcms-test-cases/` | 由 `aidlc-runner-gen.ts write` 產生 |
| 編譯產物 | `.claude/tools/data/stage-graph.json`、`scope-grid.json` | 由 `aidlc-graph.ts compile` 產生 |

兩個手寫檔需要保存；runner skill 與編譯產物都能從 stage 檔重新產生。

`aidlc-runner-gen.ts check` 只管它自己產生的 runner 集合，多一個手寫的
`tcms-verify` skill 不會讓 drift guard 紅燈（已實測）。

**不在 `.claude/` 之下、因此不受升級影響**（不需備份）：

- 撰寫標準：`aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md`
- Blocking 規則：`aidlc/spaces/default/memory/project.md` 的 `## Mandated`
- 同步工具：`scripts/tcms_sync.py`

之所以把 stage 檔放在 upstream 目錄，是因為 stage graph 的編譯器**只掃描** `.claude/aidlc-common/stages/<phase>/`（`aidlc-graph.ts` 的 `stagesDir()`；`AIDLC_STAGES_DIR` 是測試用的 seam，不是安裝點）。沒有第二個位置可放。

## 重新安裝或升級時

從 upstream 重新複製 `dist/claude/` 會**覆蓋**上述調整。覆蓋後請：

1. 重新移除 `settings.json` 的環境相依鍵（或改以 `settings.local.json` 覆寫）。
2. 重新套用 `ai-dlc-principles.md` 第 3 條的 artifacts 路徑修正 —— 先確認 upstream 是否已自行修好，若已修好則此項可刪。
3. 放回 `tcms-test-cases.md` stage 檔，然後重新產生它的衍生物：
   ```bash
   bun .claude/tools/aidlc-graph.ts compile
   bun .claude/tools/aidlc-runner-gen.ts write
   ```
   驗證兩道 drift guard 皆為 exit 0：
   ```bash
   bun .claude/tools/aidlc-graph.ts compile --check
   bun .claude/tools/aidlc-runner-gen.ts check
   ```
   並確認 stage 有進 graph（`/aidlc --doctor` 應列出 34 個 stage：aidlc 30、bootstrap 3、tcms 1，其中 `tcms-test-cases` 的 `plugin` 為 `tcms`）。upstream 若要求 reviewer stage 宣告 `review_artifact:`（2.6.121 起），tcms stage 無 `reviewer:`，不受影響。

   兩種漏做各有守門機制，不必靠記憶：

   | 漏掉什麼 | 誰會抓到 |
   |---|---|
   | stage 檔沒放回 | `scripts/validate_repo_contract.py`（已列入 `REQUIRED_FILES`）→ CI 紅燈 |
   | 放回了但沒重新編譯 | `/aidlc --doctor` 的 `Uncompiled stage files` 檢查 |

4. 跑 `bun .claude/tools/aidlc-utility.ts plugin-sync`（upstream 自 2.6.110 起要求每次升級後執行；tcms 目前不是 plugin root，會回 `no installed plugins; nothing to sync`、exit 0，這是正常的）。2.9.0 的 `doctor` 會另外把 `tcms:installed-missing` 列為 advisory warning，原因相同：stage graph 有 `plugin: tcms`，但本 repo 尚未把 tcms 整理成正式 plugin root；這不是 drift guard 失敗。
5. 對照 upstream `CHANGELOG.md` 的 **Upgrade**／**Breaking** 段逐項檢查（minor roll-up 不取代中間版本的一次性動作）。2.7.0 → 2.9.0 實測需注意：
   - **Runtime 複製來源**：2.9.0 的 manual-copy 路徑改為 release asset `aidlc-copy-runtime-2.9.0.tar.gz` 內的 `runtime/<harness>/`；從 source tag 升級時，需先以 upstream `bun scripts/package.ts claude` 產生 `dist/claude/.claude/`，再整棵替換本 repo 的 `.claude/`。
   - **Classic scope 行為**：新建 Classic intent 改為 18-stage v1 flow，走到 Build and Test 即止；若需要 2.7.0 時 Classic 含 CI Pipeline 與 Operation 的圖，改用 `workshop` scope。既有 in-flight intent 保留其記錄圖。
   - **Config / change-control 指令**：standalone `aidlc-utility.ts change-control` route 已移除，未知 `config-change` flags 會失敗；腳本若呼叫舊 route 必須改成新版 `/aidlc config` 或 `aidlc engine config set` 入口。
   - **Record runtime 檔位置**：engine 檔改放 `<record>/.aidlc-engine/`；新版仍可讀舊路徑 fallback，但新規則與 `.gitignore` 要涵蓋此目錄。
   - **Intent archive / attest**：新增 `/aidlc intent archive|unarchive`、`intent list --all`、`aidlc attest resolve|anchor`。2.9.0 前的 review 沒有 committed source evidence，attest 會回 `unverifiable`，直到下一次 per-Unit review。
   - **Native / copy runtime 拆包**：native asset 是 `aidlc-runtime-2.9.0.tar.gz`，Bun-based copy runtime 是 `aidlc-copy-runtime-2.9.0.tar.gz`，不要混用。

   2.5.33 → 2.7.0 實測踩到的四項，仍需保留在下次升級 checklist：
   - **State Version**：`grep "State Version" aidlc/spaces/*/intents/*/aidlc-state.md`，比對 `aidlc-lib.ts` 的 `CURRENT_STATE_VERSION`。舊版 state 會被 doctor 與 `next`／`report` 拒絕，upstream 不提供遷移；處置見 ADR-0013 第 3 點。
   - **規則層引用的 hook 檔名**：`grep -rn "\.claude/hooks/" aidlc/spaces/*/memory/`，被更名的 hook（如 `aidlc-mint-presence.ts` → `aidlc-record-human-turn.ts`）要同步改。
   - **`.gitignore`**：比對 upstream `.claude/CLAUDE.md` 的 Git Integration 段與 CHANGELOG 的 gitignore 項，本 repo 的 `.gitignore` 是手動維護的。
   - **殘留的舊 runner**：`git status` 應看到被更名 stage 的舊 `skills/aidlc-<old>/` 為 D；若用 `cp -R` merge copy 會留下，需手動刪。

接著跑 `/aidlc --doctor` 與 `python3 scripts/validate_repo_contract.py` 驗證。升級記錄寫入新 ADR（本次為 ADR-0014）。

## 現況

**已完整切換到 v2**（ADR-0011）：

- 專案規則位於 `aidlc/spaces/default/memory/`：`team.md`（團隊實踐）、`project.md`（專案特化）；`org.md` 僅校正整合主幹為 `ut` 與部署段落。
- AI 入口（`CLAUDE.md`、`AGENTS.md`、`.cursor/rules/`、`.agents/`）與 `scripts/validate_repo_contract.py` 均已指向 v2。
- 舊的扁平 `aidlc-docs/` 已由引擎的 flat-layout migration 整棵搬進 baseline record `aidlc/spaces/default/intents/260802-default/`；`audit.md` 轉為 `audit/<host>-<clone>.md` per-clone shard，`aidlc/.migrated` 為冪等標記。

驗證方式：`/aidlc --doctor` 與 `python3 scripts/validate_repo_contract.py` 皆須通過。
