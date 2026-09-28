# Functional Design — U-11 README 指標（問題與裁定）

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-11-readme-pointer -->

## CONDITIONAL 適用性判定：**應 skip，但引擎無法逐單元 skip**

逐款判定與理由已寫在 `business-logic-model.md` 的「適用性判定」節（含四款條件對照表），**本檔不重複**，只補上該節沒有的兩件事。

**判定摘要**：無新資料模型（交付物是 markdown 文字）、無複雜商業邏輯（單一附加動作，無分支無轉換）、無需設計的商業規則（唯二約束已在 [US:S-11] AC 1／AC 2 定死且二元可判）。

### 為什麼判定為「應 skip」卻仍有四份產出

`report --result skipped` 呼叫的是 `aidlc-state.ts skip <slug>`，作用於**整個 stage**（實測 `aidlc-orchestrate.ts:4240-4290`），會連帶跳過 U-2～U-9。引擎的 per-unit 迭代**沒有逐單元 skip 的能力**。

處置：四份照產，但內容是「判定＋理由」而非捏造的設計。依 `project.md` 的 `tcms-test-cases:c1`——判定為 0 時仍須逐項列出理由，**空檔會被下一個人讀成漏寫而非判斷**。

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T15:00:03Z（讀自 date -u） -->

### 本單元 `kind` 留空的代價，在本站具體化

units-generation 刻意讓 U-11 沒有 `kind`（「五類皆不合，收完整設計矩陣」）。後果是一段 README 文字拿到四份設計文件的待遇，含一份 `frontend-components.md`——**而 README 不是前端元件**。

**這是上游已知並接受的選擇，本站不回改。** 兩個未來可行的收斂方向已記在 `frontend-components.md`：給它更貼切的 `kind`，或讓 stage 檔對無 `kind` 者採最小矩陣而非全矩陣。

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T15:00:03Z（讀自 date -u） -->

## 送審前自檢（`project.md ## Mandated` 的六項）

| # | 項目 | 結果 |
| --- | --- | --- |
| 1 | 可達性 | 無「偵測 X 狀態」型規則 |
| 2 | 狀態欄位三問 | 無狀態欄位 |
| 3 | 引用逐字核對 | [US:S-11] AC 1／AC 2 與 [req:FR-H1] 已開檔核對 |
| 4 | 檔案集合一致性 | **本檔即為此項的產物**——自檢發現本單元缺此慣例檔 |
| 5 | 跨檔傳播 | 「應 skip 但無法 skip」的判定在 `business-logic-model.md` 與本檔一致，且兩處互相指向不重複敘述 |
| 6 | 數字重算 | 本單元的約束數為 **2**（[US:S-11] 的 AC 1、AC 2），已逐條核對 |

## 與上游的對應

單元定義與 `kind` 留空的理由引自 [ug:unit-of-work.md] 的 U-11 條目；AC 引自 `stories.md` 的 [US:S-11]（並見 [ug:unit-of-work-story-map.md] 的對應）；[req:FR-H1] 引自 `requirements.md`；「判定為 0 仍須列出理由」引自 `project.md` 的 `tcms-test-cases:c1`；`skip` 的作用域為實測 `.claude/tools/aidlc-orchestrate.ts` 所得。
