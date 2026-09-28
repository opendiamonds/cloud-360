# 約束登錄：C1 成本估算改版（上傳估價表）

本檔登錄本 intent 後續階段不得違反的約束。每條註明來源與強制等級：**Hard** 表示違反即為錯誤，**Firm** 表示需要新的決議文件才能改，**Soft** 表示可在設計階段權衡。

## 產品邊界（來自 intent-capture，已核可）

| ID | 約束 | 來源 | 等級 |
|---|---|---|---|
| P1 | 上傳式估價**完全取代**自動估價，不保留雙軌 | Q2（intent-capture） | Firm — **2026-09-16 限定**：「取代」限於**產生估價**這件事。approval-handoff 追加決定，agent 產生建議時得呼叫公開免帳號價目端點確認現價，所得價格只寫入建議文字、不回寫明細。見 ADR-0017 §8 |
| P2 | 三類建議（成本節省、跨雲比較、品質檢查）全部必備，無優先序 | Q4／Q11（intent-capture） | Firm |
| P3 | 架構師、FinOps／分析、管理層共用同一畫面，不做角色差異化 | Q3／Q10（intent-capture） | Firm |
| P4 | 本 intent 只遷移成本 agent 至 LangGraph，其餘五個模組另開 intent | Q5／Q12（intent-capture） | Firm |
| P5 | 成功指標為「上傳到取得建議的時間」 | Q6（intent-capture） | Firm |

## 技術約束（本階段確立）

| ID | 約束 | 來源 | 等級 |
|---|---|---|---|
| T1 | 各雲只支援一種主格式：AWS CSV、Azure XLSX、GCP CSV | Q1 | Firm |
| T2 | 原始檔不留存；解析後即丟棄，只持久化結構化資料 | Q2 | Hard |
| T3 | 送往 LLM 的是完整解析結果（品項、規格、數量、金額），不做裁切或遮罩 | Q3 | Firm |
| T4 | 解析失敗採寬鬆策略：能解析的照用，無法解析者標記「無法辨識」並仍產生建議，不得整批拒絕 | Q4 | Hard |
| T5 | 跨雲比較的輸入門檻為至少一朵雲；不足以比較時必須明示「資料不足」，不得靜默略過 | Q7 | Hard |
| T6 | LangGraph 經 OpenRouter 的 OpenAI 相容端點存取模型 | Q8 | Firm |
| T7 | 上傳到取得建議的目標時間為 3 分鐘內，且全程需有進度指示 | Q9 | Soft（目標值未經實測） |
| T8 | 上傳的估價表為獨立資源，可選擇性綁定架構圖，不得設為必要關聯 | Q6 | Firm |

## 退場約束

| ID | 約束 | 來源 | 等級 |
|---|---|---|---|
| R1 | 移除 `cost_router.py` 全部 9 個既有端點 | Q5 | Hard |
| R2 | 移除 4 張既有成本資料表，不保留歷史資料、不做遷移 | Q5 | Hard |
| R3 | 移除 AWS／GCP／Azure 的 Playwright calculator runner 與相關 spike 腳本 | Q5 | Hard |

## 專案既有約束（繼承，本 intent 仍受拘束）

| ID | 約束 | 來源 | 等級 |
|---|---|---|---|
| E1 | ADR-0006 安全基線：IAM、加密、網路暴露、稽核記錄四面向 | ADR-0006 | Hard |
| E2 | 核心模組需 property-based testing——解析器為純函式，明確落在範圍內 | ADR-0006 | Hard |
| E3 | 異動 schema 時 `schema_rbac.sql` 與 `DEPLOY.md` 必須同批更新 | project.md `## Mandated` | Hard（blocking） |
| E4 | 新端點需 TestClient 測試；C1 需 allow／deny 雙向授權測試 | team.md B 規則 | Hard |
| E5 | 前端行為變更需 Playwright e2e 斷言 | team.md C 規則 | Hard |
| E6 | `openapi.json` 需與端點同批 re-dump（CI 有 drift 檢查） | repo contract | Hard（blocking） |
| E7 | 每個 intent 的 construction 必經 `tcms-test-cases` stage，格式契約見 `TESTING.md` | project.md `## Mandated` | Hard（blocking） |
| E8 | 所有 record 內文件一律繁體中文 | ADR-0009 | Hard |
| E9 | 部署僅限自有 staging，production 在範圍外 | ADR-0007／ADR-0001 | Hard |

## 衝突

**C-01（~~阻擋 construction~~ — 已於 2026-09-16 由 ADR-0017 解除）**：P1「完全取代自動估價」與 `project.md` 規則 M2「必須沿用 `pricing_client` 三層計價架構」直接牴觸。M2 是為了約束舊的自動計價路徑而寫的，本改版要移除的正是那條路徑，因此 M2 在新架構下失去適用對象。這不是可以靠解讀繞過的——規則明文仍在，construction 階段會被擋。**處置：需要一份 ADR 明確廢止或改寫 M2，時點在 construction 開始之前。** 此項亦為 intent-capture 審查的 R-02 發現。

**已完成（2026-09-16）**：ADR-0017 產出於 `<record>/inception/decisions/0017-retire-automated-pricing-architecture.md`。結論是三層形狀保留、ADR-0006 的 property-based testing 落點由 `cost_calculator` 原樣移轉至估價表解析器（不是豁免）。`project.md` 三處與 `team.md` 兩處已就地加註限定，原文保留。

**同日修訂（2026-09-16T07:20Z）**：ADR-0017 §1 原本廢止 `pricing_client`，理由是「新架構無外部計價端點可包裝」。該前提在 approval-handoff 被使用者推翻——三朵雲的官網查價功能要保留。§8 因此把 `pricing_client` 恢復為 **agent 按需查價的 Port**（只對公開免帳號端點，所得價格只寫入建議文字），M2 規則的 `pricing_client` 子句隨之恢復效力。三層形狀與 PBT 移轉不受影響。C-01 仍為已解除狀態——衝突的實質（M2 要求的元件不存在）反而因 §8 而消失得更徹底。

## Assumptions & Open Questions

- ~~[open] C-01 的 ADR 尚未撰寫，也尚未決定由哪個階段負責產出。~~ → **已關閉 2026-09-16**：ADR-0017 已產出並經 §8 同日修訂。
- [open] ADR-0017 在建立後 25 分鐘內即被自我修訂，顯示 ideation 的產品邊界在 approval-handoff 仍未真正收斂。下游若再出現同類反轉，應考慮是不是該回頭重跑 intent-capture 而非繼續就地修補。
- [open] T7 的 3 分鐘是目標值不是已驗證值。設計階段需要一次真實端到端量測來確認，或者調整目標。
- [open] T2（不留存原始檔）與 E1（稽核記錄）的交互未釐清：若使用者事後質疑解析結果，沒有原始檔可回溯比對。稽核記錄要記到什麼程度尚未定義。
- [assumption] R1／R2／R3 的移除範圍以目前 codebase 盤點為準（9 端點、4 表、runner 檔案清單見 feasibility-questions.md 的 S1–S3）。若後續發現其他模組對這些端點有隱性依賴，範圍需重新確認。
