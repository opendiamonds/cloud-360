---
trigger: always_on
---

# Cloud-360 AI Agent Protocol

## 語言
ALWAYS communicate, generate documentation, and write logs in TRADITIONAL CHINESE (繁體中文).
程式碼、變數、API、識別字、專有名詞維持英文。

## AIDLC Framework Entry Point
此專案採用 [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows) 的 **AI-DLC v2**。

**Rule loading 順序**（與 `CLAUDE.md`、`.cursor/rules/ai-dlc.mdc`、`AGENTS.md` 一致）：

1. Skill 入口 `.claude/skills/aidlc/SKILL.md`（`/aidlc` 觸發）；框架結構見 `.claude/CLAUDE.md`
2. `aidlc/spaces/<active-space>/memory/` 的五層 strict-additive chain：`org.md` → `team.md` → `project.md` → `phases/<phase>.md` → stage
3. 較窄的層只能疊加，不得與較寬的層矛盾（矛盾會在 §13 learning admission check 被擋下）

詳見 `CLAUDE.md` 完整說明。

## Knowledge Base
- 框架結構與工作區慣例：`.claude/CLAUDE.md`
- 框架版本：`.claude/tools/aidlc-version.ts` 的 `AIDLC_VERSION`（`/aidlc --version`）
- Cloud-360 專屬規則：`aidlc/spaces/<active-space>/memory/team.md`、`project.md`
- AIDLC 產出（含歷史文件）：作用中 intent 的 record 目錄 `aidlc/spaces/<active-space>/intents/<record>/`

## Audit Compliance
Every AIDLC stage action is logged by the engine into the `<record>/audit/` per-clone shard — never hand-edit a shard.
Project decisions (on explicit user request only) go to `<record>/decisions-log.md`.
架構級決策開 ADR 於 `<record>/inception/decisions/NNNN-*.md`。

## Source of Truth
專案規則的單一事實來源是 `aidlc/spaces/<active-space>/memory/{org,team,project}.md`。
新增規則一律寫進 `team.md` / `project.md`；**不要**改 `.claude/` 內的 upstream 框架檔，升級時會被整批覆蓋。
