# 相位邊界檢查：Ideation → Inception

執行時間：2026-09-16T07:05Z
檢查對象：`intent-statement` → `scope-document` → `intent-backlog` 的一致性，以及範圍項目是否都有可行性背書。

## 檢查一：意圖 → 範圍的涵蓋

`intent-statement.md` 陳述的每一項產品主張，是否都在 `scope-document.md` 有對應的能力？

| 意圖主張 | 對應能力 | 狀態 |
|---|---|---|
| 使用者自行上傳三朵雲官方估價表 | CAP-1 | OK |
| agent 解析後給成本建議 | CAP-2／CAP-3／CAP-4／CAP-5 | OK |
| 省錢建議 | CAP-3 | OK |
| 跨雲比較建議 | CAP-4 | OK |
| 估價品質檢查 | CAP-5 | OK |
| 成本 agent 改用 LangGraph | CAP-6 | OK |
| 完全取代自動取價 | CAP-7 | OK |
| 三角色共用同一畫面 | scope-document「使用者與驗收」段 | OK |
| 成功指標為時間 | scope-document「成功指標」段 | OK |
| agent 得查官網現價（新增 2026-09-16）| CAP-8 | **OK，但方向相反** — 見下方註 |

**無孤兒意圖主張。**

**註（2026-09-16 重跑時追加）**：CAP-8 是在 approval-handoff 才出現的能力，`intent-statement.md` 沒有對應主張，反而有一條與它相斥的表述（「系統不再向任何外部來源取價」）。這不是孤兒能力，而是**上游未更新**。依團隊規則上游不回改，以 `decision-log.md` AH-5 與 ADR-0017 §8 向下游傳遞。下游若只讀 `intent-statement.md` 會讀到已被推翻的表述。

## 檢查二：範圍 → backlog 的涵蓋

`scope-document.md` 的每一項能力，是否都有 proto-unit 承載？

| 能力 | 承載 proto-unit | 狀態 |
|---|---|---|
| CAP-1 上傳 | PU-1、PU-2 | OK |
| CAP-2 解析與明細呈現 | PU-1、PU-4 | OK |
| CAP-3 省錢建議 | PU-6 | OK |
| CAP-4 跨雲比較 | PU-7 | OK |
| CAP-5 品質檢查 | PU-8 | OK |
| CAP-6 LangGraph 遷移 | PU-5 | OK |
| CAP-7 既有路徑退場 | PU-3 | OK |
| CAP-8 agent 按需查價 | PU-12 | OK |
| CAP-9 確定性機械檢查 | PU-11 | OK |
| （建議呈現與進度指示） | PU-9 | OK |
| （M2 ADR） | PU-10 — 已完成 | OK |

**無無主能力，亦無不對應任何能力的 proto-unit。**

## 檢查三：範圍項目的可行性背書

| 能力 | 可行性判定 | 依據 |
|---|---|---|
| CAP-1 上傳 | 可行，但為全新能力 | feasibility-assessment「技術可行性」表 |
| CAP-2 解析 | 可行，需引入試算表解析套件 | 同上 |
| CAP-3／4／5 建議 | 可行，需新的模型存取路徑 | 同上 |
| CAP-6 LangGraph | 可行 | 同上 |
| CAP-7 退場 | 可行，範圍明確可列舉 | 同上 |
| CAP-8 agent 查價 | **有條件可行** | 公開端點確實存在（AWS Bulk、Azure Retail、GCP Catalog），但 SKU 對應是舊系統的失敗點（RISK-07）。非阻塞設計使衝擊可控 |
| CAP-9 機械檢查 | 可行，且不依賴外部服務 | 純程式判定，不需 SKU 對應，是本 intent 少數確定性可交付的部分 |
| 三分鐘指標 | **有條件可行** | 同上；已放寬至 5 分鐘上限並要求實測 |

**所有範圍項目皆有可行性背書。** 唯一「有條件」的項目（時間指標）已在 scope-definition 取得放寬後的上限，並指派 nfr-requirements 實測。

## 檢查四：矛盾偵測

| 檢出 | 性質 | 處置 |
|---|---|---|
| IC-4（三類全必備、不分先後）vs SD-1（省錢為核心 Must，另兩類 Should） | **字面矛盾，已知且刻意** | reviewer R-01 指派 scope-definition 收斂；上游不回改，以 decision-log SD-1 註明性質向下游傳遞 |
| SD-1（品質檢查降 Should）vs AH-1（要求補機械檢查） | **非矛盾** | 兩者防的是同一個風險的不同層次：前者是 LLM 自然語言判斷，後者是程式判定。已列入 initiative-brief 的義務表 |
| SD-3（同批部署）vs SD-7（value-first） | **非矛盾，但有組合後果** | 產生一段「有明細沒建議」的窗口期。已在 scope-document、initiative-brief 與 Consolidated Summary 三處揭露；AH-2（兩人以上可平行）讓它有機會壓縮 |
| FE-2（不留原始檔）vs ADR-0006 稽核要求 | **未解衝突** | 事後無原始檔可回溯，稽核粒度未定。已指派 domain-design |
| IC-2／FE-5（完全取代、`pricing_client` 全刪）vs AH-5（保留 agent 查價）| **字面矛盾，已就地修訂** | ADR-0017 §8 撤回 §1／§3 的相關斷言；`constraint-register.md` P1 已加限定；`scope-document.md` CAP-7 已把 `pricing_client.py` 移出退場清單。§1／§3 已標注不得單獨引用 |
| AH-5（agent 查價）vs AH-1／CAP-9（機械檢查）| **非矛盾，但極易被誤合併** | 查價由 LLM 決定查什麼，不具確定性，不能當機械檢查用。已在 ADR-0017 §8、`scope-document.md` CAP-9、`raid-log.md` RISK-01 三處明寫兩者不得合併 |

## 檢查五：阻塞項

| 項目 | 狀態 |
|---|---|
| ADR-0017（M2 規則衝突） | **已解除**（同日經 §8 修訂，結論仍為解除）|
| `deploy/render-env.sh` repo contract 違規 | **已解除 2026-09-16**：AWS 帳號憑證傳遞整條移除；`validate_repo_contract.py` 與 `validate_env_contract.py` 皆通過 |

## 檢查六：完整性標記

| 標記 | 範圍 | 影響 |
|---|---|---|
| `drifted` | `scope-definition` | 漂移來源為 ADR-0017 後的狀態註記編輯，未動決策。判定不重跑（AH-4） |
| `untracked` | `workspace-scaffold`、`workspace-detection`、`state-init`、`feasibility` | 完成時未留 `orchestrate report` 收據。Advisory，不擋路由 |

## 結論

**通過，無未完成的前置條件。**

意圖、範圍、backlog 三者一致，無無主能力；所有範圍項目有可行性背書；兩項阻擋（M2 規則衝突、repo contract 違規）皆已解除。檢出的六項張力中五項已有明確處置，一項（稽核粒度）已指派 domain-design。

**通過但值得記下的一件事**：本報告在 2026-09-16 同日重跑了一次。第一次通過之後，使用者在核可關卡提出保留官網查價功能，推翻了三站的定案並觸發 ADR-0017 的自我修訂。反轉的範圍已被壓到最小、所有受影響產出已就地更新，但這代表產品邊界到 ideation 最後一站仍在移動。若 inception 再出現同類反轉，重跑 intent-capture 會比繼續就地修補便宜。

## 人工核可

- [ ] 已檢視本報告並同意進入 Inception
