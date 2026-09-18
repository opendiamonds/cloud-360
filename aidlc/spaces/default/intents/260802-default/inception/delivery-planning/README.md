# Inception Plans

> AIDLC inception-phase planning artifacts for Cloud-360.
> Cloud-360 inception 階段的規劃產出。

### 目錄內容

`aidlc-docs/inception/plans/` 存放 AIDLC inception 階段（workflow planning / unit planning / cross-pillar 排程）的規劃產出。

| 檔案 | 說明 |
|---|---|
| [`development-plan.html`](development-plan.html) | 9 個支柱 / 26 條 user story 的 wave-based 開發計劃，內容已繁中化；含 Kanban 看板、相依圖、story table、pillar 細節、NFR 與風險。**建議用瀏覽器開啟**：`open aidlc-docs/inception/plans/development-plan.html`。 |
| [GitHub Project（live）](https://github.com/users/opendiamonds/projects/16) | live kanban，26 個 draft items（標題前綴 `[Cloud-360]`），自訂欄位：Wave / Pillar / Story ID。Status 內建 Backlog / Ready / In progress / In review / Done。可直接拖卡片改狀態。 |

### 與其他 inception 子目錄的關係

- `requirements/` — SRS（需求規格）來源。
- `user-stories/` — pillar 與 user stories 來源。
- `application-design/` — system architecture（agent routing、integration layer 等）。
- `decisions/` — ADRs（架構級決策）。
- `plans/`（**本目錄**） — 把上述輸入整理成可執行的 wave 與 sprint。

### 維護準則

- 計劃檔案（HTML / md）更新時要記錄到 `aidlc-docs/audit.md`。
- 涉及範圍變動（例如新增 pillar、wave 重切）需另開 ADR。
- markdown 檔案（例如本 README）必須雙語（per ADR-0005）；HTML 內也建議含中英對照區塊。
