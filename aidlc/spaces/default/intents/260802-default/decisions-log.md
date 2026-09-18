# Project Decisions Log

> 在使用者明確要求時記錄的專案重要決議。規則見 [`aidlc/spaces/default/memory/team.md`](../../memory/team.md) 的 `## Mandated`。

### 紀錄

#### 2026-05-09 23:29:39 +0800 — 換掉 ai-logging，改用 on-demand decisions-log

**Decision / 決議**: 移除 per-turn 強制 log 機制（`.ailog/` 與 `.aidlc-overrides/ai-logging.md`），改為**僅在使用者明確要求時記錄**的 `aidlc-docs/decisions-log.md`。重點從「逐 turn 操作」轉為「重要決議」，大幅降低 log 雜訊與 PR 遞迴噪音。
**Context / 背景**: ai-logging 機制（PR4 引入、PR #16 加 deferred-logging clause）強制每個 turn append entry，pure-ops turn 還會引發單一 PR 遞迴；實際使用後發現絕大多數 turn 細節不值得記，需要被保留的是「重要決議」而非「每個 keystroke」。
**Trigger / 觸發語**: 「幫我將ai-logging 規則移除，新增一個專案重要決議記錄，當使用這要求時，就記錄當下與AI對話的決議」
**Related / 相關**:
- PR #17（本 PR；branch `danniel/feat/decisions-log-rule`）
- Supersedes PR4（`.ailog/` 與 ai-logging.md 引入）與 PR #16（deferred-logging clause）
- 舊 `.ailog/2026-05-09.md` Turn 1–4 內容保留在 git 歷史（PR4 / PR #14 / PR #15 commits）
