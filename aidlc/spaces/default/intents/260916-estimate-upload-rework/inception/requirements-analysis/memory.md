# Stage Memory: requirements-analysis

## Interpretations

- 2026-09-16T09:55Z — Step 1 的 authoritative description 取自 `project-description` 工具，`source: project-description.json`，未由 audit 的 `Request` 重建。使用者本輪未提供任何 pasted document，故 `.aidlc-document-input-path` 未建立、`document-input` 未呼叫。
- 2026-09-16T09:55Z — Step 3 深度判定為 **Standard**（與 `aidlc-state.md` 第 18 行一致）。判定依據：scope 邊界已由 ideation 四站收斂、codekb 提供了完整的既有實作事實，剩餘未知集中在「全新資源的授權模型」與「全新輸入面的安全界線」兩處，屬中等範圍而非大規模未知。
- 2026-09-16T09:55Z — Step 5 六面向完整度評估的缺口落點：**功能需求**大致齊備（ideation 已定 CAP-1 至 CAP-9）；**非功能需求**缺上傳面的安全界線與稽核粒度；**使用者情境**缺多使用者可見性與重複上傳語意；**業務脈絡**齊備；**技術脈絡**由 codekb 補足，但既有 RBAC story id 的處置未決；**品質屬性**缺機械檢查的可驗證判準。八題即依此六面向的缺口生成，不依樣板題庫。
- 2026-09-16T09:55Z — 問題全部紮在 reverse-engineering 的實測事實（[S1]–[S8]），而非一般性最佳實務。例如 Q1 的存在理由是 `cost_service.py:43` 跨模組借用 `collab_router` 私有函式這個具體發現，不是抽象的「要考慮權限」。

## Deviations

- 2026-09-16T09:55Z — 生成 8 題，接近 stage-protocol 建議上限。未再壓縮的理由：Q1／Q2 是同一個 RBAC 主題的兩個獨立決策（資源可見性 vs story id 存廢），合併會迫使使用者以單一選項同時回答兩件不相干的事；Q6／Q7 分屬稽核與正確性兩個面向，亦不可併。

- 2026-09-16T10:10Z — Step 8 觸發三題後續澄清（F1–F3），全部源自**跨題交互**而非單題模糊。F1：Q7 的 0.5% 容差與已定案的 FE-4 寬鬆解析互斥——只要有一列無法辨識，逐列加總必然偏離表上總額遠超 0.5%，該檢查在部分解析檔案上會恆為失敗。F2：Q5 的「保留但預設不顯示」語意不完整，且與 scope 的「歷史版本比較未承諾」貼邊。F3：Q1 的「沿用架構圖分享模型」實質新增了 CAP 清單外的能力。三者若不解決會直接寫出無法實作或越界的需求。

## Tradeoffs

- 2026-09-16T10:10Z — **如實記錄 scope 成長 vs 悄悄吸收**。F2 與 F3 的答案（歷史清單檢視、分享列為 Must）都超出 ideation 已核可的 CAP-1～CAP-9。選擇在 `requirements.md` 的 OQ1 明記「本 stage 新增、scope-document 尚未涵蓋」並要求回補，而非把它們當作既有 CAP 的自然延伸寫進去。代價是 scope-definition 的 drift 再增兩項、下游需要一次回補作業；收益是 scope 文件不會與實際承諾脫節。此決定在提問當下即以「按下確認前需要知道的兩個後果」向使用者揭露，非事後補記。
- 2026-09-16T10:10Z — **FR9 退場清單採逐條可執行形式而非概括敘述**。把 reverse-engineering 盤點出的 8 類套件外掛鉤全部展開成 FR9.1–FR9.11，含具體行號與檔名（如 `validate_cost_calculator_boundary.py` 須改寫而非刪除、六個設定檔須連動）。代價是需求文件變長且與實作細節貼近，偏離「需求不談實作」的一般原則；理由是這些掛鉤的遺漏後果是 CI 紅燈而非設計瑕疵，且 codekb 的盤點結果若不在此固定下來，下游沒有第二次機會發現。

- 2026-09-16T10:25Z — **就地修訂 vs 退回 ideation**。F4 於摘要確認環節以 Other-escape 形式提出，推翻了四層既有約束（`project.md` `## Never`、`team.md` Q2、ADR-0017 §3／§8、repo contract 腳本的字串攔截），影響面達到「本可主張退回 scope-definition 重跑」的程度。選擇在 requirements 就地吸收並以 OQ6–OQ8 標記待辦，理由與 approval-handoff 的 AH-5 同型：退回會使已核可的 ideation 四站全部重開，而此變更的性質是**增加一條既有模組的使用許可**（`pricing_sdk` 由刪改留），不是推翻產品邊界——上傳仍是估價唯一來源，agent 查價仍只寫入建議文字。代價是 requirements 成為第二個記載規則推翻的地方（第一個是 ADR-0017），追溯時須同時讀兩處。
- 2026-09-16T10:25Z — **F4 的端點分類先於裁決**。使用者原話是「呼叫三朵雲各自的 api，可以是需要帳號的」，字面上涵蓋 Cost Explorer 類。未直接照字面寫入需求，而是先區分「目錄價類」與「實際帳單與用量類」兩種憑證 API 的風險輪廓再請裁示，結果收斂到只解禁目錄價類（FR5.7 維持帳單類禁令）。這使 ADR-0018 的論據可以立在「`pricing:GetProducts` 讀不到帳戶內任何資源」之上，而非泛泛的「需要更準的價格」。若照字面實作，ADR-0001 的 production credentials 邊界會被實質推翻。

- 2026-09-16T10:35Z — 附加作者回應時使用字串切片 `s[:s.index("## Review")]`，把 reviewer 剛寫入的整個 `## Review` 區段截掉。檔案未進版控，無 git 可還原。以 resume 方式請原 reviewer 重新附上，並明確要求「不要因為知道已修正就改寫或刪減，保留審閱當下的原始意見」——避免還原成一份被結果污染的事後版本。reviewer 另加了 `### 審閱者後續意見` 確認 R-06／R-07 的處置。**教訓**：對已有下游 agent 寫入內容的檔案做附加時，不得用 index 切片截尾，應以純 append 或錨定在自己寫入的標記上。

## Open questions

- [open] OQ1–OQ5 已寫入 `requirements.md`。其中 OQ1（scope 回補）需在進入 domain-design 前處理，其餘四項各有指定的下游歸屬階段。
