# 意圖聲明：C1 成本估算改版（上傳估價表）

## Problem Statement（問題陳述）

現行 C1 成本估算由系統自行取得價格：讀架構圖、對 SKU、打公開價目端點或自動操作官方 Calculator。這條路太慢或太常失敗（逾時、產品對不到、需要重試），使用者等不到結果。[Q1]

改版把「取得價格」交還給使用者：使用者自行上傳 AWS／Azure／GCP 三朵雲的官方估價表，由 agent 解析後給成本建議。[desc]

同時改掉現行 agent 框架。[desc] 成本估價 agent 改用 LangGraph。[Q5][Q12]

## Target Customer（目標對象）

三種角色都會使用這個功能：架構師（自己畫完架構、自己到官方 Calculator 估完價，需要一個地方彙整三朵雲並拿到建議）、FinOps／成本分析角色（接收別人做好的估價表，負責審視與提出優化建議）、專案或管理層（只想看到三朵雲的總額與比較，不參與估價過程）。[Q3]

介面不做角色差異化，三者看到的是同一個畫面。[Q10]

agent 要輸出三類建議，且不分先後、三類必須同時具備才算完成：省錢建議（指出哪些項目偏貴、可以換規格／改計費模式／用保留量方案）、跨雲比較建議（同一套架構在三朵雲的成本差異與取捨）、估價品質檢查（指出估價表本身的漏項、規格與架構不符、數量不合理）。[Q4][Q11]

## Success Metrics（成功指標）

- 從上傳到看到建議的時間。[Q6]

## Initiative Trigger（為何是現在）

自動取價太慢或太常失敗，使用者等不到結果。[Q1]

## Initial Scope Signal（範圍訊號）

- Workflow-selected scope：`c1-estimate-upload-rework`。[scope]
- 使用者確認沿用這個範圍與階段安排（20 個階段、17 道核可關卡）。[Q9]
- 產品邊界：完全取代。本次之後估價只有「使用者上傳」這一條路，自動取價與自動填 Calculator 整組退場。[Q2]
- 框架遷移邊界：本 intent 只做估價改版（含成本 agent 用 LangGraph），其餘五個走 `claude-agent-sdk` 的模組另開 intent 遷移。[Q12] 六個模組最終一律遷移到 LangGraph、不保留兩套框架，是跨 intent 的方向。[Q5]

## Assumptions & Open Questions

- [assumption] Q6 選項文字以「例如 3 分鐘內完成」為舉例，使用者未確認具體門檻數字。實際目標值待 scope-definition 或 nfr-requirements 確立。
- [assumption] Q2 的「完全取代」使既有 `pricing_client` 與自動取價路徑退場，而 [memory:M1]（C1 價目來源禁用需憑證的計價 API、`pricing_client` 只准公開免帳號價目端點）與 [memory:M2]（cost 功能域三層架構加獨立 `pricing_client`）都是針對現行架構寫的規則。這兩條規則在新架構下要如何改寫或保留，本階段無法判定。
- [assumption] 由使用者上傳檔案會引入既有系統沒有的未信任輸入面（檔案格式、內容、大小）。本階段未取得任何關於檔案來源信任程度的答覆，此風險留給 feasibility 階段評估。
- [assumption] 既有 9 個掛在 `/diagrams/...` 之下的成本端點與 Cost 頁面的退場方式（直接移除、保留相容期、或改寫）未在本階段確認。

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-09-16T05:00:41Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/ideation/intent-capture/intent-statement.md > Target Customer（目標對象）` | Q11 答案 D 使三類 agent 輸出（省錢建議、跨雲比較、估價品質檢查）全部列為必備且不分優先順序，同時沒有任何 MVP 備援邊界。若三類中有一類在 feasibility 評估後技術困難或時程不足，目前沒有預先定義的優先排序可供取捨，scope-definition 與 construction 都會面臨「全做或全改需求」的抉擇。 | 人工確認是否接受「三類全部必備」的高執行風險；若存有任何優先順序共識，應在 scope-definition 明確登錄，而非留白到 construction 才暴露。 | New |
| R-02 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/ideation/intent-capture/intent-statement.md > Assumptions & Open Questions` / `aidlc/spaces/default/intents/260916-estimate-upload-rework/ideation/intent-capture/intent-capture-questions.md > Assumption Confirmation 第 2 項` | [memory:M2] 為 dated-affirmed（2026-08-19）規則，明文要求 cost 功能域維持三層架構並保留獨立的 `pricing_client` 層。Q2 選 A「完全取代」使自動取價路徑整組退場，這在結構上衝突 M2 對 `pricing_client` 存在的強制要求。產出物將此標記為「accepted assumption」，但「已確認方向改寫既有 affirmed 規則」的情況在本專案的慣例下需要新 ADR，而不是一般假設的接受。若進入 construction 才被擋，返工代價高。 | 人工確認在進入 inception 或最晚 construction 前，是否需要先開一張 ADR 明確廢止或修改 M2 的 `pricing_client` 強制要求；或確認 M2 在新架構下改寫的方向，讓後續各 stage 有遵循依據。 | New |
| R-03 | Minor | `aidlc/spaces/default/intents/260916-estimate-upload-rework/ideation/intent-capture/intent-statement.md > Success Metrics（成功指標）` | 成功指標僅列「從上傳到看到建議的時間」，且第 1 項 assumption 已明確承認具體門檻數字未確認。對於 ideation 階段屬正常留白；但整個 `## Success Metrics` 區塊只有一個指標，指標本身也無任何方向性範圍（例如「比現行自動估價快 X 倍」），後續 NFR-requirements 需從零確立，風險在於門檻難以反推回使用者期望。 | 無強制行動；建議在 scope-definition 取得一個大致量級（即使是方向性的），避免 NFR-requirements 無錨點可用。 | New |
| R-04 | Minor | `aidlc/spaces/default/intents/260916-estimate-upload-rework/ideation/intent-capture/stakeholder-map.md > 關係人與其關注點` | Q7 只選 C（維運這個 repo 的人），使三種使用者角色（架構師、FinOps、管理層）被明確排除在「關鍵關係人」之外，僅以附記方式保留在表格中。若這個 initiative 最終影響到這三種角色的工作流程（例如 Cost 頁面 UI 改版），缺乏其代表可能導致 inception 階段的使用者故事缺少驗收人。 | 無強制行動；建議人工確認三種使用者角色是否需要指名一位代表作為 inception 使用者故事的 acceptance owner。 | New |
| R-05 | Minor | `aidlc/spaces/default/intents/260916-estimate-upload-rework/ideation/intent-capture/intent-capture-questions.md > Sources > [memory:M1] 與 [memory:M2]` | 來源登錄顯示 `project.md### Forbidden` 與 `project.md### Mandated`，疑為路徑分隔符 `#` 與 H2 heading 的 `##` 合併產生三重 `###`。stage 規格要求格式為 `path.md#<exact H2 heading>`（單一 `#` 分隔、heading 名稱不含 markdown 前綴）。若 `claim-sources` sensor 以嚴格 H2 格式驗證，此兩項登錄可能被視為無效來源，連帶使所有引用這兩條記憶規則的聲明失去來源支撐。 | 無強制行動；建議在 sensor 回報錯誤前先確認 `claim-sources` 對此格式的容錯行為；若 sensor 擋下，修正為 `project.md#Forbidden` 與 `project.md#Mandated`。 | New |

### Summary

產出物在意圖捕捉階段的完整度合格：五個必要區塊齊備、每個實質聲明均附來源標記、兩份產出物都包含 `## Assumptions & Open Questions`、Assumption Confirmation 已完成並接受全部 7 項假設。主要需人工確認的風險有兩點：三類 agent 輸出「全必備、不分優先」的範圍承諾（R-01），以及已知會與 dated-affirmed 記憶規則 M2 衝突的架構方向（R-02）——後者建議在進入 construction 前明確以 ADR 處理，而非仰賴假設接受機制帶過。
