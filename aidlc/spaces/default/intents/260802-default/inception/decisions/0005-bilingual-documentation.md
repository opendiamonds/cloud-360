# ADR 0005: Bilingual Documentation

> ⚠️ **Superseded by ADR-0009**（文件改為一律繁體中文）。本 ADR 保留作歷史紀錄。

- Status: Accepted
- Date: 2026-05-02
- Amendment 2026-05-09: ADR-0006 PR2 後文件位置改為 `aidlc-docs/`，本 ADR 的雙語要求自動延伸至 `aidlc-docs/**/*.md`。

## Context

Cloud-360 會由中文使用者、國際協作者、AI agent、dev-agent 與不同技術角色共同閱讀與維護。為避免規格理解落差，所有專案文件必須同時提供中文版與英文版。原規範針對 `docs/**/*.md`；ADR-0006 PR2 後遷移至 `aidlc-docs/**/*.md`，雙語要求不變。

## Decision

所有 `aidlc-docs/**/*.md` 文件必須包含：

- `## 中文版`
- `## English Version`

文件可以採同檔雙語模式，不必拆成兩個檔案。第一階段採同檔雙語，降低文件同步成本。

## Requirements

- 新增或修改 `aidlc-docs/` 文件時，必須同步更新中文與英文內容。
- README 可以保持產品入口，但需連到雙語 docs。
- SRS、Architecture、User Stories、ADR 都必須雙語。
- CI 的 repository contract validation 必須檢查 `aidlc-docs/` 文件是否包含雙語章節（PR2 後 docs/ 不再存在）。

## Consequences

- 中文團隊可以快速討論產品與架構。
- 英文 reviewer、外部 contributor 與 AI agent 可以理解規格。
- 文件變更成本略增，但能降低跨語言誤解風險。