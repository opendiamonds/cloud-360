# Domain Entities — U-11 README 指路段落

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-11-readme-pointer
     本單元的 `kind` 依 [ug:unit-of-work.md] 刻意留空（「五類皆不合，收完整設計矩陣」），
     故 `produces_kinds` 解析出**全部四份**產出。本檔是其中之一。 -->

## 適用性判定

**本單元沒有領域實體。** 這是判定，不是漏寫。

交付物是 `README.md` 中的一段 markdown 文字。它沒有欄位、沒有值域、沒有生命週期狀態、不與任何其他實體發生關係。[ad:component-dependency.md] 已明記「FR-H1（README 指路）為單段文字，**無元件**」，[ad:component-methods.md] 因此也沒有本單元的任何型別或方法簽章。

## 本單元碰到的唯一外部識別字

| 名稱 | 性質 | 說明 |
| --- | --- | --- |
| Project #16 | **外部資源的識別字**，不是本系統的實體 | 組織 `opendiamonds` 的 Project 編號。本單元只是在文字中引用它的 URL，不讀它、不寫它、不解析它 |

> 注意這與 U-1／U-3 的處理**性質不同**：那些單元把 Project 編號當作 `Config` 的參數並據以呼叫 API（[F1=A] 要求不得寫死）；本單元是在**給人看的散文**裡放一個連結。散文中的連結不適用「不得寫死」的參數化要求——那條約束的目的是讓機制可被其他 repo 重用，而 README 本來就是本 repo 專屬的。

## 與上游的對應

單元邊界引自 [ug:unit-of-work.md] 的 U-11；故事對應引自 [ug:unit-of-work-story-map.md]；FR-H1 引自 `requirements.md`；「無元件」的判定引自 [ad:component-dependency.md]，[ad:component-methods.md] 與 [ad:services.md] 均無本單元的對應項，此為上游的明確結論。
