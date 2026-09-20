<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations

- 2026-09-16T16:30Z — CONDITIONAL stage 適用性：condition 為「需要新元件或邏輯構件時執行；純屬既有元件修改則略過」。本 intent 是**替換**而非修改——既有 18 支 `backend/cost/` 模組中大部分退場、解析器與 agent 為全新構件、資料模型整套換掉。適用性明確成立。
- 2026-09-16T16:30Z — `user-stories` 為 SKIP，`stories.md` 不存在，故 traceability 依 stage 檔 Step 6 的 fallback 規則列舉 `requirements.md` 的每一條 FR（FR1–FR11 的所有子項），而非 `USx.y`。
- 2026-09-16T16:30Z — 本站另承接三件上游明文指派的未決事項：`requirements.md` OQ3（架構圖綁定語意）、OQ4（FR7.3 授權來源），以及 requirements-analysis 審閱 R-06 被作者裁定延後至 domain-design 的新解析器模組命名（因 `validate_cost_calculator_boundary.py` 硬編碼路徑且檔案不存在即 CI 紅燈，命名未定會讓 FR9.6 無法實作）。三者皆已編為本站問題（Q5、Q6、Q7）。
- 2026-09-16T16:30Z — ensemble mode 為 `inline`，support agents（`aidlc-aws-platform-agent`、`aidlc-design-agent`）不另行派工，其視角由本 stage 內部承擔。
- 2026-09-16T16:30Z — 依 stage 檔明示，entity 只捕捉到「ownership + shape」層級（擁有者、識別子、屬性名、跨元件參照），**不**指定型別、驗證約束、允許值與關聯基數——那些屬 functional-design 的 `entities.md`。

## Deviations

- 2026-09-16T17:05Z — `traceability.json` 有 **11 項 GAP**，遠高於一般比例。全部集中在兩類：FR9 的純刪除與工具鏈維護項（FR9.3、9.7、9.8、9.9、9.10、9.11）、FR11 的部署設定項（FR11.1、11.2、11.3），另加 FR5.8（憑證注入管線）與 FR10.4（範圍排除的宣告，本質上不應有 target）。這些不是覆蓋不足，是**本 intent 有近三分之一的需求不由任何應用構件實現**——它是替換而非新建，退場面與部署面的份量本來就大。如實標記並逐項寫明落點（infrastructure-design、deployment-pipeline、build-and-test、contract-design），不強行對應到元件以美化數字。
- 2026-09-16T17:05Z — 目錄中納入兩個**既有且本期不改動**的元件（`IdentityAndRbac`、`Collaboration`）。stage 檔的完備性規則要求「每個 `owned_by` 指名的元件都必須是已宣告元件」，而 `EstimateSet` 參照 `User` 與 `UserDiagram`。不宣告它們會使目錄不合法；宣告它們則需明確標注「不改動」以免被誤讀為本期工作範圍。選擇後者並在 summary、`behaviour` 與摘要表三處重複標注。
- 2026-09-16T17:05Z — 本檔的 ADR 編號為 `ADR-001`…`ADR-007`，與 repo 層級的 `ADR-0001`…`ADR-0018`（位於 `inception/decisions/`）是**不同序列**。stage 檔要求「Number ADRs sequentially (ADR-001, ADR-002, …)」，照辦，但在 `decisions.md` 檔首明文警示此混淆風險並要求引用時加上路徑或「domain-design ADR-00N」前綴。

## Tradeoffs

- 2026-09-16T17:05Z — **`EstimateSet` 是本站推導而非需求明文**。`requirements.md` 從未使用「批次」一詞，但 FR5.3（跨雲比較）、FR6.3（歷史清單）、FR6.6（分享）三者的對象都是「一次上傳」而非「單朵雲的估價表」。不引入批次，這三件事都沒有可掛載的對象。代價是多一層間接（`EstimateSet → Estimate → EstimateLineItem`）與一個需求沒說的概念。若日後發現使用者期望以單朵雲為分享與歷史的單位，這是第一個該被推翻的決定（記於 `components.md` A-DD1）。
- 2026-09-16T17:05Z — **機械檢查結果不持久化，每次重算**。換得的是「存下來的結論與現在算出來的不同」這類漂移永遠不會發生——這類漂移只能靠人工比對發現，是最難察覺的一類缺陷。代價是每次讀取都重算，但以單次最多三份、每份數十列的規模可忽略。此決定是 Q2=B（獨立純函式驗證器）的直接紅利，若驗證器併進協調層就享受不到。
- 2026-09-16T17:05Z — **Q7=A 讓 `backend/cost/` 套件名留下來但裡面幾乎全換**。換得單一進入邊（C6）維持不變與 CI 腳本只改一行。代價是套件名與新職責語意不貼合，日後讀 code 的人會困惑為什麼上傳功能在 `cost` 底下。明確承受此技術債（`components.md` OQ-DD1）。落選的 `backend/estimate/` 語意最貼切，但會新增第二條進入邊而破壞 C6。
- 2026-09-16T17:05Z — **Q5=A ＋ Q6=B 讓架構圖綁定變成一個幾乎沒有行為的欄位**。換得的是 FR7.3 的跨模組私有函式引用**自然消失**（不是改用別的引用，是根本不需要引用），且不必為此新增 `services/diagram_access` 元件、不必動既有 `services` 套件。代價是使用者可能預期綁定有更多意義。

## Open questions

- 2026-09-16T17:05Z — **`AdviceOrchestrator` 的背景工作在單一 FastAPI process 下有卡死風險**。部署拓樸為單一 process（codekb `architecture.md`），process 重啟會遺失進行中的工作，而 `Advice` 是在工作開始時就以「產生中」狀態建立的——重啟後該筆會永久停在「產生中」。需要逾時清理機制。執行機制本身（`BackgroundTasks`／`asyncio` task／外部 worker）屬 units-generation 與 infrastructure-design，但這條約束必須傳下去（`components.md` OQ-DD3）。
- 2026-09-16T17:05Z — **綁定架構圖可能洩漏私有圖的存在**。若 A 看得到一個綁定了 B 的私有架構圖的估價批次，UI 會顯示該架構圖的 id 或標題，等於洩漏「B 有一張這個名字的圖」。緩解方式是 UI 只在呼叫者本身有權看該圖時才顯示標題，否則顯示為「已綁定（無權檢視）」或隱藏。記於 domain-design ADR-005 的 Consequences，交由 functional-design 落實。
- 2026-09-16T17:05Z — **「重新上傳一朵雲」的語意未定**。`EstimateSet` 引入後，使用者在已有批次的情況下再丟一個檔案，是加進現有批次還是開新批次？refined-mockups 的 M3 顯示「＋ 再上傳一份估價表」暗示前者，但 FR6.2 說「每次上傳建立一筆新紀錄」暗示後者。交由 functional-design（domain-design ADR-003 的 Consequences）。
- 2026-09-16T17:05Z — 既有 `pricing_client` 在 `backend/cost/.pricing_offer_cache/` 寫 24 小時磁碟快取，而 `pricing_cache` 資料表隨 FR9.2 退場。磁碟快取的去留 `requirements.md` 未提及，`PricingLookup` 保留或移除它交由 functional-design（`components.md` OQ-DD2）。
