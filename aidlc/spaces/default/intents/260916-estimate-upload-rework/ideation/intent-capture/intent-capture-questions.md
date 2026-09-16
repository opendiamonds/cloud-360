## Sources

- [desc] Initial description: "C1 成本估算改版：改掉現行 agent 框架；使用者直接上傳 AWS／Azure／GCP 三朵雲的官方估價表，由 agent 解析後給成本建議"
- [scope] Workflow-selected scope: `c1-estimate-upload-rework`.
- [memory:M1] `aidlc/spaces/default/memory/project.md### Forbidden`: "**NEVER** 呼叫需要雲端供應商帳號憑證的計價 API（Cost Explorer、Billing、Cost Management 等）作為 C1 價目來源；`pricing_client` 只准公開免帳號價目端點 (affirmed 2026-08-19)"
- [memory:M2] `aidlc/spaces/default/memory/project.md### Mandated`: "**ALWAYS** cost 功能域採三層：`cost_router` → `cost_service` → 純函式 `cost_calculator`，另獨立 `pricing_client`；禁止把 cost 邏輯寫進 `user_router.py` 或 `wa_rule_engine.py`；`cost_calculator` 內禁止 httpx、DB session、`HTTPException` (affirmed 2026-08-19)"

<!-- 上列四項是本 stage 的完整可用來源範圍。背景知識、通則與推論不得登錄為來源。 -->

## 出題前查證（非來源，僅供題幹與選項設計參考）

<!-- 依 project.md ## Corrections 的既有規則：ideation 的「禁實作細節」約束的是 artifact 內容，不是查證行為。
     下列查證結果只用來把問題問對，不得寫進 intent-statement.md 或 stakeholder-map.md，也不得作為來源引用。 -->

- `backend/cost/` 現有 30 個檔，估價路徑是「讀架構圖 XML → 對 SKU → 打公開價目端點／以 Playwright 自動填官方 Calculator」。
- `backend/cost/cost_router.py` 現有 9 個端點，全部掛在 `/diagrams/...` 之下（含 xlsx／csv 匯出、region、每列時數／SKU／單價覆寫、稽核）。
- 全 repo 有 6 個後端模組 import `claude-agent-sdk`：`services/design_agent.py`、`services/review_agent.py`、`services/wa_lens_engine.py`、`services/llm_provider.py`、`services/prompt_guard.py`、`cost/cost_pricing_agent.py`。`backend/requirements.txt` 只列 `claude-agent-sdk`，無 langchain／langgraph。

---

## Q1. 這次改版要解決的核心問題是什麼？

現行做法是系統自己去取得價格（讀架構圖、對 SKU、打官方價目端點或自動操作官方 Calculator）。改成由使用者上傳官方估價表，等於把「取得價格」這件事交還給使用者。請說明是哪一個痛點促成這個轉向。

- A. 系統自動取得的價格不準或覆蓋不足，使用者不信任那個數字
- B. 自動取價太慢或太常失敗（逾時、產品對不到、需要重試），使用者等不到結果
- C. 使用者本來就會在官方 Calculator 上做估價，再讓系統重做一次是多餘的
- D. 維護 SKU 對照與三朵雲各自的取價路徑成本太高，想把這塊整個拿掉
- X. Other (please specify)

<!-- 選項收斂紀錄：初稿另有「E. 尚未定義／以上皆非，我想描述別的問題」。
     提問介面每題上限 4 個選項，故於提問前先收斂本檔。
     合併方式：E 的語意（以上皆非、想自行描述）與 X. Other 完全重疊，直接移除 E，不新增選項。 -->

[Answer]: B

## Q2. 上傳估價表之後，現行「跟著架構圖自動估價」那條路要怎麼處理？

這題決定本次改版的產品邊界，也決定既有的 `/diagrams/...` 成本端點與 Cost 頁面是留、是改、還是退場。

- A. 完全取代：本次之後估價只有「使用者上傳」這一條路，自動取價與自動填 Calculator 整組退場
- B. 並存但上傳為主：兩條路都留，畫面預設走上傳，自動估價降為輔助或備援
- C. 並存且互補：上傳的官方數字與系統自動算的數字並列呈現，讓使用者比對差異
- D. 尚未定義：這輪先把上傳做出來，舊路怎麼收尾之後再決定
- X. Other (please specify)

[Answer]: A

## Q3. 誰會上傳這些估價表？他們現在的痛點是什麼？

請指出主要使用者。若對象與既有角色（架構師、FinOps 分析師、管理者）不同，請在 Other 說明。

- A. 架構師：自己畫完架構、自己去官方 Calculator 估完價，需要一個地方彙整三朵雲並拿到建議
- B. FinOps／成本分析角色：接收別人做好的估價表，負責審視與提出優化建議
- C. 專案或管理層：只想看到三朵雲的總額與比較，不參與估價過程
- D. 以上多者皆是（請在 Other 說明各自的差別）
- X. Other (please specify)

[Answer]: D（各角色差別由 Q10 追問）

## Q4. 「agent 給建議」具體是指哪一類建議？

這決定 agent 讀完估價表之後要輸出什麼，也決定成功與否要怎麼衡量。

- A. 省錢建議：指出哪些項目偏貴、可以換規格／改計費模式／用保留量方案
- B. 跨雲比較建議：同一套架構在 AWS／Azure／GCP 的成本差異與取捨建議
- C. 估價品質檢查：指出估價表本身的問題（漏項、規格與架構不符、數量不合理）
- D. 以上皆要（請在 Other 說明優先順序）
- X. Other (please specify)

[Answer]: D（優先順序由 Q11 追問）

## Q5. 換成 LangGraph 的範圍是什麼？

目前有六個後端模組走同一套 `claude-agent-sdk`：架構圖產生（design agent）、架構審查（review agent）、Well-Architected lens 引擎、共用的 LLM provider、prompt 防護，以及成本估價 agent。換框架的範圍不同，風險與工作量差距很大。

- A. 只換成本這塊：新的估價建議 agent 用 LangGraph，其餘五個模組維持現狀
- B. 全部換掉：六個模組一律遷移到 LangGraph，不再保留兩套框架
- C. 新的用 LangGraph、舊的原地不動：不設遷移期限，容許兩套並存
- D. 尚未定義：這輪先確認方向，範圍留待可行性評估後決定
- X. Other (please specify)

[Answer]: B

## Q6. 這次改版要達成什麼可衡量的結果？

請選出最能判斷「這次改版成功了」的指標。可複選（select all that apply）。

- A. 從上傳到看到建議的時間（例如 3 分鐘內完成，相對於現行自動取價的逾時問題）
- B. 三朵雲的估價表都能被正確解析的比例
- C. 建議本身的價值：使用者採納的比例，或建議指出的可節省金額
- D. 尚未定義：這輪不設量化指標
- X. Other (please specify)

<!-- 選項收斂紀錄：初稿為 A–E 五個選項，其中「D. 既有自動取價相關的程式碼與維護負擔減少的幅度」、
     「E. 尚未定義：這輪不設量化指標」。提問介面每題上限 4 個選項，故於提問前先收斂本檔。
     合併方式：移除初稿的 D（程式碼與維護負擔減少幅度）——它是 Q2 選擇「完全取代」時的衍生後果，
     不是本功能對使用者的成功指標，改由 Q2 的答案承接；初稿的 E 遞補為現行的 D，文字不變。 -->

[Answer]: A

## Q7. 這次改版有哪些關鍵關係人，各自在意什麼？

可複選（select all that apply）。請在 Other 補充任何不在清單上的角色。

- A. 只有你自己：需求、範圍、驗收都由你一人決定，沒有其他關係人
- B. 使用這個功能的架構師／分析師：在意上傳是否順暢、建議是否可信
- C. 維運這個 repo 的人：在意舊估價程式碼退場後的維護負擔與部署風險
- D. 尚未識別：這輪還無法指名
- X. Other (please specify)

[Answer]: C

## Q8. 這次改版的進度與決策需要向誰回報，頻率為何？

- A. 不需要：沒有對外回報要求，決策在對話中即時做掉
- B. 需要，但只在每個階段的核可關卡確認即可，不另外產出報告
- C. 需要固定節奏的書面回報（請在 Other 說明對象與頻率）
- D. 尚未定義
- X. Other (please specify)

[Answer]: B

## Q9. 目前這個工作流程選定的範圍是 `c1-estimate-upload-rework`，這與你心中的產品邊界一致嗎？

這個範圍會執行 20 個階段、共 17 道核可關卡，涵蓋從需求、設計、實作到部署的完整流程（跳過市場研究、團隊組建、CI pipeline 建置、觀測與事件應變等 14 個階段）。

- A. 一致：確認沿用這個範圍與階段安排
- B. 範圍太大：想縮成更輕的流程（請在 Other 說明想砍掉哪些）
- C. 範圍不對：我心中的產品邊界與這個描述不同（請在 Other 說明實際邊界）
- D. 一致，但想調整詳細程度（Depth）或測試強度（Test Strategy）
- X. Other (please specify)

[Answer]: A

<!-- 以下為 batch 1 答覆後新增的追問。Q3 與 Q4 均選 D（以上皆是），
     原題要求在 Other 補充差別與優先順序，改以獨立追問處理。 -->

## Q10.（追問 Q3）三種角色都會用，那誰是這次改版的主要對象？

介面與流程只能為一種角色最佳化，其餘兩者遷就。請指出以誰為準。

- A. 架構師為主：介面圍繞「我剛估完價，想知道該怎麼改」設計
- B. FinOps／成本分析角色為主：介面圍繞「審視別人的估價表並產出優化意見」設計
- C. 管理層為主：介面圍繞「三朵雲總額比較與結論」設計，細節收折
- D. 不分主次：三者看到的是同一個畫面，不做角色差異化
- X. Other (please specify)

[Answer]: D

## Q11.（追問 Q4）三類建議都要，哪一類是第一順位？

第一順位決定 agent 的預設輸出，以及沒時間做完時先保住哪一塊。

- A. 估價品質檢查優先：數字先可信，才談優化
- B. 省錢建議優先：使用者最想看到的是「哪裡可以省」
- C. 跨雲比較優先：使用者最想看到的是「哪一朵雲比較划算」
- D. 不分先後：三類必須同時具備才算完成
- X. Other (please specify)

[Answer]: D

## Q12.（追問 Q5）六個模組全面遷移，要不要跟這次估價改版綁在同一個 intent 交付？

Q5 選 B，遷移對象含三個與成本無關的模組（design agent、review agent、WA lens 引擎）。這決定本 intent 的交付邊界與風險。

- A. 綁在一起：本 intent 一次做完估價改版與六個模組的 LangGraph 遷移，全綠才算完成
- B. 同一個 intent、分兩階段：先做成本這塊並把 LangGraph 基座立起來，其餘五個模組在同一 intent 的後段分批遷
- C. 拆成兩個 intent：本 intent 只做估價改版（含成本 agent 用 LangGraph），其餘模組另開 intent 遷移
- D. 尚未定義：等可行性評估看過遷移成本再決定
- X. Other (please specify)

[Answer]: C

## Assumption Confirmation

兩份產出（`intent-statement.md`、`stakeholder-map.md`）目前帶有以下 7 項 `[assumption]`：

1. Q6 的「3 分鐘內」只是選項舉例，具體門檻數字未確認。
2. Q2 的「完全取代」使 `pricing_client` 與自動取價路徑退場，[memory:M1]、[memory:M2] 兩條既有規則在新架構下如何改寫或保留無法判定。
3. 使用者上傳檔案引入未信任輸入面（格式、內容、大小），風險程度未評估。
4. 既有 9 個 `/diagrams/...` 成本端點與 Cost 頁面的退場方式未確認。
5. Q7 指認的「維運這個 repo 的人」是決策者還是影響者、具體對象為誰，未說明。
6. Q3 指認的三種使用者角色，其對範圍或優先順序的決策權未確認。
7. 除核可關卡之外是否有對外回報對象，未被排除。

- A. Accept assumptions（接受，保留 `[assumption]` 標記帶進後續階段）
- B. Convert to follow-up questions（轉成追問，現在就解掉）

[Answer]: A. Accept assumptions

## Consolidated Summary Confirmation

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
