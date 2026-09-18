# Cloud-360 對 AI-DLC v2 安裝的調整

本目錄由 upstream [`awslabs/aidlc-workflows`](https://github.com/awslabs/aidlc-workflows) 的 `v2` 分支產出複製而來。除下列**兩處**外，內容與 upstream 一致。

版本的單一事實來源是 `.claude/tools/aidlc-version.ts` 的 `AIDLC_VERSION`（跑 `/aidlc --version` 可查），目前為 **2.5.33**。初次並行安裝為 2.5.11（upstream commit `257b43a`，見 commit `4f2b626`）。

## 調整 1：`settings.json` 移除環境相依設定

upstream 的 `settings.json` 是**進版控**的共享檔案，預設帶著 AWS workshop 情境的設定。原樣 commit 會強制本 repo 的每位開發者走 Bedrock，沒有 AWS 憑證者會直接失敗。

已移除下列項目：

| 項目 | upstream 預設 | 移除原因 |
|---|---|---|
| `CLAUDE_CODE_USE_BEDROCK` | `1` | 強制走 Bedrock；本團隊未必都使用 |
| `AWS_REGION` | `us-east-1` | 環境相依 |
| `ANTHROPIC_DEFAULT_*_MODEL` | `global.anthropic.*` | Bedrock 專用 model ID，非 Bedrock 環境無效 |
| `AWS_AIDLC_DEFAULT_SCOPE` | `workshop` | 教學用 scope，不適合真實功能開發；改為由 `/aidlc` 依描述自動偵測 |
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

## 重新安裝或升級時

從 upstream 重新複製 `dist/claude/` 會**覆蓋**上述兩處調整。覆蓋後請：

1. 重新移除 `settings.json` 的環境相依鍵（或改以 `settings.local.json` 覆寫）。
2. 重新套用 `ai-dlc-principles.md` 第 3 條的 artifacts 路徑修正 —— 先確認 upstream 是否已自行修好，若已修好則此項可刪。

接著跑 `/aidlc --doctor` 與 `python3 scripts/validate_repo_contract.py` 驗證。

## 現況

**已完整切換到 v2**（ADR-0011）：

- 專案規則位於 `aidlc/spaces/default/memory/`：`team.md`（團隊實踐）、`project.md`（專案特化）；`org.md` 僅校正整合主幹為 `ut` 與部署段落。
- AI 入口（`CLAUDE.md`、`AGENTS.md`、`.cursor/rules/`、`.agents/`）與 `scripts/validate_repo_contract.py` 均已指向 v2。
- 舊的扁平 `aidlc-docs/` 已由引擎的 flat-layout migration 整棵搬進 baseline record `aidlc/spaces/default/intents/260802-default/`；`audit.md` 轉為 `audit/<host>-<clone>.md` per-clone shard，`aidlc/.migrated` 為冪等標記。

驗證方式：`/aidlc --doctor` 與 `python3 scripts/validate_repo_contract.py` 皆須通過。
