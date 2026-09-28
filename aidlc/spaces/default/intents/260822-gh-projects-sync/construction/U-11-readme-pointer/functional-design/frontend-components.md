# Frontend Components — U-11 README 指路段落

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-11-readme-pointer
     本單元的 `kind` 依 [ug:unit-of-work.md] 刻意留空（「五類皆不合，收完整設計矩陣」），
     故 `produces_kinds` 解析出**全部四份**產出。本檔是其中之一。 -->

## 適用性判定

**本單元沒有前端元件。** 這是判定，不是漏寫。

`README.md` 是 repo 根目錄的一份 markdown 檔，由 GitHub 的 repo 首頁渲染。它不是本專案 `frontend/` 之下的 React 元件，沒有 props、沒有 state、沒有互動流程、沒有表單驗證、沒有 API 整合點——這五項正是本檔按 stage 檔定義應該涵蓋的內容，五項全部不適用。

## 為什麼這份檔案還是被要求產出

[ug:unit-of-work.md] 的 U-11 條目把 `kind` **刻意留空**，理由逐字是「五類皆不合，收完整設計矩陣」。而 functional-design 的 `produces_kinds` 把 `frontend-components` 限於 `kind: ui`，對**未標註**的單元則套用全矩陣——於是一段 README 文字拿到了四份設計文件的待遇。

**這是 units-generation 已知並接受的選擇，不是本站發現的缺陷。** 記在此處是為了讓那個選擇的實際代價有一個具體落點：下次若有同類單元（純文件、無 kind），可考慮在 units-generation 給它一個更貼切的 kind，或讓 stage 檔對「無 kind」採最小矩陣而非全矩陣。

## 本單元真正的呈現面

唯一「使用者看得到的東西」是 GitHub repo 首頁上多出的一段文字。它的受眾是 **P2（協作者）**——[US:S-11] 的主 persona 在 Revision 1 由 P3 改為 P2，理由是 P3 依定義不進 repo，而該故事的 goal 逐字是「我從 repo 進來時」。

驗收不經任何前端工具鏈：R-1 是 grep、R-2 是 `git diff --numstat`（見 `business-rules.md`）。

## 與上游的對應

`kind` 留空的理由與其後果引自 [ug:unit-of-work.md] 的 U-11 條目；persona 的更正引自 `stories.md` 的 S-11；FR-H1 引自 `requirements.md`；故事對應引自 [ug:unit-of-work-story-map.md]；「無元件」的判定引自 [ad:component-dependency.md]，[ad:component-methods.md] 與 [ad:services.md] 均無對應項。
