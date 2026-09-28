# Business Rules — U-11 README 指路段落

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-11-readme-pointer
     本單元的 `kind` 依 [ug:unit-of-work.md] 刻意留空（「五類皆不合，收完整設計矩陣」），
     故 `produces_kinds` 解析出**全部四份**產出。本檔是其中之一。 -->

## 規則清單

本單元只有兩條規則，兩條都直接來自 [US:S-11] 的 AC，**本站未新增任何規則**。

| # | 規則 | 可判定方式 | 來源 |
| --- | --- | --- | --- |
| R-1 | `README.md` 存在一段含 Project #16 連結的文字，說明該看板是需求清單的正本 | 文字比對（grep 連結） | [US:S-11 AC 1]、[req:FR-H1] |
| R-2 | 與變更前比對，`git diff --numstat` 對 `README.md` 的**刪除行數為 0** | `git diff --numstat -- README.md` 的第二欄 | [US:S-11 AC 2] |

## 為什麼只有兩條

stage 的 condition 中「business rules need design」對本單元**不成立**——上面兩條不需要設計，它們在 user-stories 站就已經是二元可判的最終形式。R-2 尤其是刻意被改寫成這個形狀的：原措辭「既有結構與總覽敘述未被改動」不可判，改為刪除行數為 0 之後才同時具備二元性與可 grep 性。

## 與既有檢查的重疊（不是缺陷）

[ug:unit-of-work.md] 的 U-11 實作註記與 [US:S-11 AC 2] 的註都指出：本單元與全域 DoD 的 `validate_repo_contract.py` 有部分重疊——該腳本的 `REQUIRED_TEXT` 已鎖住 README 的關鍵字。

**下游不需為此另設檢查。** 這一句是上游明文寫下的，記在此處是為了避免下一個人把重疊誤讀成「有兩套規則要維護」。

## 與上游的對應

規則來源為 `stories.md` 的 S-11 AC 1／AC 2 與 `requirements.md` 的 FR-H1；單元的完成判準引自 [ug:unit-of-work.md] 的 U-11 條目；故事歸屬引自 [ug:unit-of-work-story-map.md]；[ad:component-dependency.md] 判定本單元無元件，[ad:component-methods.md]／[ad:services.md] 因此無對應項。
