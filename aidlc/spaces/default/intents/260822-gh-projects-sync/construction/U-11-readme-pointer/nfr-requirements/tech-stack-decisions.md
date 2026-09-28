# Tech Stack Decisions — U-11 README 指路段落

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-11-readme-pointer
     `kind` 依 [ug:unit-of-work.md] 刻意留空，故解析出**全部五份**產出。 -->

## 適用性判定

**本單元沒有技術選型。** 交付物是 `README.md` 中的一段 markdown 文字——沒有 runtime、沒有依賴、沒有建置步驟、沒有執行環境。

stage 的 condition 有一款是「tech stack selection needed」，對本單元不成立；另一款「Skip if no NFR requirements and **tech stack already determined**」——markdown 連 stack 都談不上，比「已決定」更前面一步。

## 沿用的既有技術事實

| 事實 | 出處 | 對本單元的意義 |
| --- | --- | --- |
| `README.md` 由 GitHub 的 repo 首頁直接渲染，不經任何建置 | [kb:technology-stack.md]（該檔盤點的建置產物清單不含 `README.md`） | 沒有工具鏈可選，也沒有版本要 pin |
| `validate_repo_contract.py` 的 `REQUIRED_TEXT` 已鎖住 `README.md` 的關鍵字 | `project.md ## Mandated`、[ug:unit-of-work.md] U-11 實作註記 | 唯一會碰到這個檔的自動化是既有的 contract 驗證，本單元不新增任何工具 |

## 與上游的對應

單元定義與「無需另設檢查」的判斷引自 [ug:unit-of-work.md] 的 U-11；本單元無商業邏輯與領域實體的判定見同單元的 `business-logic-model.md` 與 `business-rules.md`；FR-H1 引自 `requirements.md`；既有技術棧事實引自 [kb:technology-stack.md]。
