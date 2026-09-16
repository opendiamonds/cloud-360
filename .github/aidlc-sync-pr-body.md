由 `aidlc-sync-pull` 自動產生（ADR-0012 階段 2）。

## 這個 PR 包含什麼

只有**狀態鏡像**：`github-status.md` 與 `aidlc-sync-state.json`。

**不含任何內容變更** —— story 敘述、驗收標準、實作單元的真實來源是 repo，反向同步不碰它們（ADR-0012 的逐欄位切分）。

## 為什麼要開 PR 而不直接推 ut

反向同步是唯一可能繞過 AI-DLC approval gate 的路徑。PR 化讓它必須經過人眼。

## 變更明細

見 commit 訊息。狀態欄位（open/closed、assignee、labels）以 GitHub 為真實來源 —— 人在看板上拖卡片、指派、關閉 issue 本來就是正式操作。

## 這個 PR 不會觸發正向同步

commit 訊息帶 `[aidlc-sync]` 前綴，正向同步 workflow 會排除它（防迴圈第 2 道）。
