# Phase Boundary Verification — Ideation → Inception

<!-- Stage: approval-handoff（Ideation 1.7）· 依 stage-protocol-governance.md §13 與 verification.md 方法執行。
     檢核對象：intent-capture、feasibility、scope-definition、rough-mockups 的已核可 artifacts（market-research、team-formation 依 scope 跳過）。 -->

## 檢核範圍與方法

- **Intent → Scope → Intent Backlog 一致性**：逐項比對 intent-statement 確認的產品邊界、scope-document（Revision 1）的 Must 集合、intent-backlog 的 proto-units。
- **Scope 項目的 feasibility backing**：逐項比對五項 Must 能力與 feasibility-assessment／constraint-register 的評估涵蓋。

## 一致性檢核：Intent → Scope → Backlog

| Intent 確認的邊界 | Scope 對應 | Backlog 對應 | 狀態 |
| --- | --- | --- | --- |
| 稽核需最後一次登入（活動）時間，預留歷史擴充路徑 | Must (a) 記錄 | PU-1 | ✅ 完整追溯 |
| Admin 介面顯示每帳號時間值 | Must (b) 顯示 | PU-2 | ✅ 完整追溯 |
| 超過 N 天未活動帶視覺標示 | Must (c) 視覺標示 | PU-3（N 值定案為前置） | ✅ 完整追溯 |
| `Security_Reviewer` 檢視權限開通 | Must (d) 權限開通 | PU-4 | ✅ 完整追溯 |
| （rough-mockups Q5a 擴充，經 scope-definition Revision 1 核可） | Must (e) 卡片改造 | PU-5 | ✅ 完整追溯（擴充走了回跳修訂重審協定） |

- 欄位語意由「最後登入」定錨為「最後活動」（feasibility Q1/Q8）：依 learned rule 不回改上游，以問題檔確認紀錄向下游傳遞 — 語意鏈一致，無矛盾。
- Won't Have 四項與「未承諾」一項（稽核報表匯出）在 intent 與 scope 間無衝突；未承諾狀態未被推定為排除或範圍。
- 無孤兒 artifact：ideation 產出均可回溯至 intent-statement 或經核可的修訂決議。

## Feasibility backing 檢核

| Scope 項目 | Feasibility 依據 | 狀態 |
| --- | --- | --- |
| (a) 記錄 | 技術可行性表「活動紀錄／認證模型／資料儲存」三列；成本警示 R1 記入 raid-log | ✅ |
| (b) 顯示 | 「管理介面」列：表格式清單機械性擴充，無疑慮；空窗處置 Q2 | ✅ |
| (c) 標示 | 空值不套標示（Q2）；N 值依賴記於 raid-log D2 | ✅ |
| (d) 權限開通 | 「權限矩陣」列：翻轉一筆權限值＋兩處 seed 同步（T5）；風險接受 R3 | ✅ |
| (e) 卡片改造 | ⚠️ 後於 feasibility 納入（Revision 1）：純前端、不觸發 schema 變更，介面可行性由「管理介面可延伸」評估間接涵蓋；前端回歸風險已記於 scope-document assumptions 與 PU-5 DoD | ⚠️ 間接涵蓋（可接受） |

## 檢核結論

- **Intent captured** ✅（intent-statement 經 4 輪 review READY）
- **Scope defined** ✅（scope-document Revision 1 經重審核可）
- **Feasibility confirmed** ✅（conditional GO 四前提均已落地；(e) 為間接涵蓋，風險已記錄）
- **Initiative approved** ⏳（本 verification 先於 approval-handoff gate 產出；gate 核可即完成此項）

**警示（非阻擋）**：PU-5 無獨立的 feasibility 評估輪次，其可行性依據為間接涵蓋＋風險記錄；若 inception 的 refined-mockups 或 application-design 發現卡片改造有結構性障礙，應依協定回跳處理。

**整體判定：PASS（帶一項非阻擋警示）** — 可交接進 Inception。

## Human Approval

- [ ] 使用者於 approval-handoff gate 核可（gate 核可即視為本檢核的人工確認）
