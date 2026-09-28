# Phase Check — Inception → Construction

**執行時間**：2026-08-29T04:16:48Z（`date -u`）
**執行方式**：機械計數與集合比對（腳本），非人工目視。每一項下方註明抽取方式，讓下一個人可獨立複驗。

## 檢查結果總覽

| # | 檢查項 | 結果 | 抽取方式 |
| --- | --- | --- | --- |
| ① | requirements canonical ID 集合 | **55 條**（FR 40 ＋ NFR 15） | `grep -oE '(FR\|NFR)-[A-Z][0-9]+'` 於 `requirements.md` |
| ② | 全部故事的需求標籤都指向真實需求 | **✅ 無野標籤** | `stories.md` 抽出的 ID 集合 − canonical ＝ ∅ |
| ③ | 全部需求都被故事承接 | **✅ 55/55，無孤兒** | canonical − `stories.md` 抽出的 ID 集合 ＝ ∅ |
| ④ | 架構涵蓋全部需求 | **✅ 55/55，無野標籤、無未涵蓋** | 五份 application-design artifact 併集比對 canonical |
| ⑤ | 故事對應到單元 | **✅ 11/11 故事、12/12 單元** | `unit-of-work-story-map.md` 對 `stories.md` 與 `unit-of-work.md` 的 ID 集合 |
| ⑥ | Bolt 計畫涵蓋全部單元 | **✅ 12/12，無單元落在任何 Bolt 之外** | 四份 delivery-planning artifact 併集比對 `unit-of-work.md` 的 `### U-` 標題 |
| ⑦ | 依賴圖無環、無懸空引用 | **✅ 12 節點／21 邊／DFS 無環** | 解析 `unit-of-work-dependency.md` 的 yaml edge block |
| ⑧ | Bolt 序列滿足全部 DAG 邊與同批次約束 | **✅** | 對修訂後 edge block 逐 Bolt 重放 |

## 逐項說明

### ② ③ 需求 ↔ 故事雙向

canonical 55 條中，直接標在 AC 上的與列在 `stories.md` 全域 Definition of Done 表的，合起來覆蓋全部 55 條。**沒有需求落空，也沒有指向不存在編號的標籤。** 這是雙向檢查——只做單向（故事的標籤都合法）不會發現「有需求沒人承接」。

### ④ 架構 ↔ 需求

五份 application-design artifact（`components.md`、`component-methods.md`、`services.md`、`component-dependency.md`、`decisions.md`）併集後對 canonical 比對，兩個方向都是空差集。

### ⑤ 故事 ↔ 單元

`unit-of-work-story-map.md` 涵蓋 11 則故事與 12 個單元，無空單元、無未對應故事。**S-2 與 S-3 各有一條 AC 橫跨兩個單元**（判定屬 U-1、清單成員身分屬 U-7），這是刻意的切分結果而非遺漏——故事依「可觀察的成果」切、單元依「驗證方式與失敗模式」切，兩把尺不同。

### ⑦ ⑧ 依賴與序列

12 節點、21 邊、DFS 無環、無懸空 `depends_on` 目標、`kind` 全為合法值（U-11 依 `unit-of-work.md` 明記「五類皆不合」而留空，yaml 與 artifact 一致）。

Bolt 序列 1「U-1～U-6 ＋ U-10a」／2「U-7」／3「U-8 ＋ U-10b」／4「U-9」／5「U-11」逐一重放，滿足：全部 DAG 邊、三組真捆綁（U-6＋U-1～U-5、U-4＋U-10a、U-8＋U-10b）、一條不可覆寫排序邊（U-6 → U-8）。

## 帶進 Construction 的未結項目（不是檢查失敗，是已知且已追蹤的缺口）

這四項全部通過上述機械檢查，但它們是**已標出而尚未關閉**的事實。列在此處是為了讓它們跨過 phase 邊界時不被遺失：

| # | 項目 | 落點 | 風險 |
| --- | --- | --- | --- |
| G-1 | `ReconcileReport` 缺 `undecidable` 欄位，使 [US:S-2 AC 4] 目前不可滿足 | functional-design 增設該欄位（Bolt 2） | 該 stage 為 **CONDITIONAL 且 per-unit**，U-7 那輪若被判「無新資料模型」而 skip，修補會連帶被跳過 |
| U-3 的 403 半邊 | [US:S-10 AC 5] 的第二個例子（改 record 目錄以外的檔案回 403）在本設計下無機制 | PRE-1-a 實測（Bolt 0）決定 | 不適用時該 AC 需回 user-stories 改寫，**不得**在 Bolt 4 逕自標為通過 |
| over-suppression | 反向同步的逐 intent 歸屬未驗證，先例形狀不同 | Bolt 3 實測 | 全域暫停而非逐 intent |
| [req:OQ-7] | 既有三支 `scripts/aidlc_sync_*.py` 的遷移 | **本 intent 之外**，需另立 intent | 不在任何 Bolt 內，不得被誤讀為已排程 |

## 判定

**Inception → Construction 邊界檢查通過。** 八項全綠，四項未結事項已各自指派落點並在 `bolt-plan.md` 與 `risk-and-sequencing-rationale.md` 有對應的 gate。
