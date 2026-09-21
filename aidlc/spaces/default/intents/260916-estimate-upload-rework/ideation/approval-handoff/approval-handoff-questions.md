# Approval & Handoff 問題：C1 成本估算改版（上傳估價表）

本檔為 ideation 最後一站的提問與作答紀錄。彙整型 stage 只問未被上游定案的事項，省略清單見 [S5]。

## Sources

- **[S1]** `ideation/feasibility/raid-log.md`：6 項風險、5 項假設、4 項問題、7 項依賴。其中 ISSUE-01（M2 規則衝突）、ISSUE-02（三類建議無優先序）、DEP-04（ADR）已於 2026-09-16 解決；ISSUE-03（`deploy/render-env.sh` 的 `AWS_SECRET_ACCESS_KEY`）與 ISSUE-04（測試污染）仍在。
- **[S2]** `ideation/scope-definition/intent-backlog.md`：10 個 proto-unit，PU-10 已完成。第一梯次（依賴為空）為 PU-1 解析器、PU-3 退場、PU-5 LangGraph 骨架；open item 明載「四項是否真能平行，取決於是否有足夠人力」。
- **[S3]** `python3 scripts/validate_repo_contract.py` 於 2026-09-16T07:00Z 執行仍回 `ERROR: Forbidden secret-like content found: deploy/render-env.sh: AWS_SECRET_ACCESS_KEY`。`validate_env_contract.py` 通過。此為目前唯一擋住 CI 綠燈的項目。
- **[S4]** 引擎的 `stage_validity` 於本 stage 進入時回報：`Completed stage results have drifted; routing is continuing in advisory mode. Suggested redo: /aidlc --stage scope-definition.`。`directly_stale: ["scope-definition"]`。漂移來源為 ADR-0017 完成後回頭標註狀態的編輯（`scope-document.md` 前置依賴表、`intent-backlog.md` PU-10 列）。另有四站列為 `untracked`（workspace-scaffold、workspace-detection、state-init、feasibility），因其完成時未經 `orchestrate report` 留下收據。
- **[S5]** 已由上游定案、本階段不重問：意圖與範圍的共識（scope-definition Q8＝A，由 Danniel 一人代表三種角色驗收，且各階段核可關卡即為確認機制，intent-capture Q8＝B）；範圍邊界與排除清單（scope-definition Q5）；交付排序偏好（Q7＝B value-first）；時間指標（Q6＝B）；三類建議的優先序（Q1＝B）。stage 檔範例題中的「rough mockups 是否反映共同願景」「market research 是否支持投資」「mobs 是否已配置排程」三題省略：`rough-mockups`、`market-research`、`team-formation` 三站在本 scope 均為 SKIP，沒有對應產出可確認。

---

## Q1 — 風險接受

feasibility 登錄的六項風險中，四項需要在進 inception 前明確接受或退回 [S1]：

- **RISK-01 解析靜默錯誤**：欄位對錯不報錯，agent 照著錯數字給有自信的建議。唯一防線（品質檢查建議）在 scope-definition 已降為 Should。
- **RISK-02 三分鐘可能不可達**：瓶頸全在 LLM 推論，若同樣逾時，改版沒解決「太慢太常失敗」的原始問題。
- **RISK-03 完整估價內容送第三方**：本地不留原始檔，但解析後完整內容送進 OpenRouter。
- **RISK-04 兩套 agent 框架並存**：本 intent 只遷成本 agent，期間兩套框架、兩條模型存取路徑。

- **A.** 四項全部接受，帶著風險進 inception
- **B.** 接受三項，但 RISK-01 要求在 inception 補上機械檢查的設計（不只靠 LLM 判斷）
- **C.** 接受三項，但 RISK-02 要求在 inception 就做一次真實端到端計時，不等到 nfr-requirements
- **D.** 先不接受，回頭調整範圍

[Answer]: B <!-- 2026-09-16T07:03Z -->

## Q2 — 人力與平行度

intent-backlog 的第一梯次有三項技術工作依賴為空、理論上可平行（PU-1 解析器、PU-3 退場、PU-5 LangGraph 骨架），但能否真的平行取決於人力 [S2]。這會直接決定 value-first 的實際順序與那段「有明細沒建議」的窗口期長度。

- **A.** 單人作業——序列執行，delivery-planning 依此排 Bolt
- **B.** 有兩人以上可平行
- **C.** 單人，但可用多個 AI agent 平行跑不同 unit
- **D.** 尚未確定，留給 delivery-planning 時再定

[Answer]: B <!-- 2026-09-16T07:03Z -->

## Q3 — `deploy/render-env.sh` 的 repo contract 紅燈

ISSUE-03 目前是唯一擋住 CI 綠燈的項目 [S3]。它不是本 intent 引入的，但本 intent 的任何 PR 都會因它紅燈。

- **A.** 現在就處理，在進 inception 之前清掉
- **B.** 進 inception，但在第一個 code 變更的 PR 之前處理
- **C.** 留到 construction 開始前處理
- **D.** 另開 issue／intent 處理，不佔本 intent 的階段

[Answer]: A <!-- 2026-09-16T07:03Z -->

## Q4 — scope-definition 的漂移處置

引擎回報 `scope-definition` 已漂移，建議重跑 [S4]。漂移來源是 ADR-0017 完成後回頭把「已解決」狀態標進該站產出——改動只涉及狀態註記，沒有動任何決策或答案，但引擎比對的是指紋不是語意。

- **A.** 不重跑，在 decision-log 記明漂移來源與判定理由，帶著 advisory 標記前進
- **B.** 重跑 scope-definition（八題會重問一次）
- **C.** 不重跑，且把「核可後不得回頭編輯該站產出」列為往後的作業規則

[Answer]: A <!-- 2026-09-16T07:03Z -->

---

## Consolidated Summary Confirmation

- **Q1**：接受 RISK-02、RISK-03、RISK-04 三項風險。RISK-01（解析靜默錯誤）**不只接受**——要求 inception 補上機械檢查的設計，不得只靠 LLM 判斷。
- **Q2**：有兩人以上可平行，第一梯次三項技術工作（解析器、退場、LangGraph 骨架）可同時起跑。
- **Q3**：`deploy/render-env.sh` 的 repo contract 紅燈現在就清掉，在進 inception 之前。
- **Q4**：不重跑 scope-definition，在 decision-log 記明漂移來源與判定理由。

**需要在按下確認前看到的三個後果：**

1. **Q1 的 B 在 scope 上加了一項新義務。** scope-definition 把品質檢查建議（CAP-5）降為 Should，意思是最壞情況下可以不交付；Q1=B 現在要求另外設計一套不依賴 LLM 的機械檢查。兩者不衝突——CAP-5 是「agent 用自然語言指出可疑數字」，機械檢查是「程式判定總額對帳、幣別一致、數量落在合理範圍」——但這是一項上游沒有的新設計義務，必須進約束登錄並指派給 functional-design，否則會在階段之間掉包。

2. **Q2 的 B 改變了窗口期的性質。** 單人序列時，「有明細沒建議」的窗口期由交付速度決定；兩人以上可平行時，PU-5（LangGraph 骨架）與 PU-1／PU-2／PU-4（上傳到明細）可同時推進，窗口期有機會壓到接近零。這讓 delivery-planning 的排程空間變大，但也意味著 value-first 這個排序偏好的實際約束力下降——它原本是為了在資源有限時決定先做什麼。

3. **Q3 的 A 會在本 stage 核可之後立即產生一次 code 變更。** `deploy/render-env.sh` 不是本 intent 的範圍內物件，修它屬於範圍外的順手處置。這不影響 ideation 的任何決策，但會讓本 intent 的第一個 commit 包含一個與估價改版無關的修正，commit 訊息需要據實反映。

[Answer]: Looks correct <!-- 2026-09-16T07:20Z -->
