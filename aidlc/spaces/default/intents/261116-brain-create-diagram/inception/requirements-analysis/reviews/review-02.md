## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-11-17T05:34:17Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR1.3、FR1.4、FR6.3 | 「產圖失敗後使用者再說一次，大腦接著畫同一張草稿」缺一個可成立的銜接。FR1.3 只規定「新建完成後」作業對象切到新圖，沒說建圖成功但產圖失敗時作業對象是否已切到草稿。若沒切，使用者再說一次時作業對象仍是系統，會再走 FR2.2 判定；系統下已有一張草稿，p 高時就再建第二張，與 FR6.3「不另建新圖」及 FR1.4 衝突。FR1.4 與 NFR3 只覆蓋同一工作項內的重試，不覆蓋「新的一句話」。系統下有多張草稿時，「同一張」要怎麼指也沒有規則。 | 明寫失敗時作業對象的狀態（建議建圖成功即切到草稿）。補上「再說一次」遇到系統下有未完成草稿時的規則：沿用、反問，或新建。補一條可測 AC，例如「建圖成功、產圖失敗，再說一次，系統下仍只有一張圖」。 | Resolved (reviewer) |
| R-02 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR1.2、FR2.2、FR2.4 | 判定規則在「系統下沒有圖」時有未定義的區間。FR1.2 寫「判定為新建或語意中性時直接新建」，但 FR2.2 只定義 p ≥ 0.7、1−p ≥ 0.7、其餘反問；「語意中性」沒有對應的 p 範圍。依 FR2.2，0.3 < p < 0.7 一定反問，依 FR1.2 同一句卻應直接新建，兩者互相牴觸。FR2.3 的性質「(0.3, 0.7) 一定反問」又把 0.3／0.7 寫死，而門檻實際是可調設定（`intent_routing_config.py` 的 `BRAIN_ROUTER_CONFIDENCE_THRESHOLD`，無預設值，初版 0.7）。「語意中性」的出處也只標 [IC:Q3]，但 Q3 的前提是作業對象已有圖，無圖情況的來源其實是 [IC:Q1] 與 [desc]。 | 用 p 區間列出「有圖／沒圖」兩種情況的完整判定表，涵蓋 p ≥ t、p ≤ 1−t 與兩者之間；刪除或定義「語意中性」。FR2.3 的性質改以門檻 t 表達，不寫死 0.3／0.7。FR1.2 的來源標籤改為 [IC:Q1]，或標明是設計者推導。 | Resolved (reviewer) |
| R-03 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR6.4 | 草稿只被規定在三種清單（專案頁、工作區歷史清單、切換對象選單）標示。其他消費「系統下的圖」的路徑沒有表態：被選為作業對象後交辦評核、估成本；估價與 WA 評核的圖選取；分享清單；專案頁以外其他依 `system_id` 統計或列出圖的地方。空白草稿被拿去評核或估價，會得到錯誤或誤導的結果，而這正是使用者不知道草稿存在時最容易發生的路徑。FR6.5 只管既有資料與回滾，沒有盤點這些消費者。 | 列出所有讀取 `user_diagrams` 的消費者（評核、估價、分享、專案頁統計、切換對象），各自規定對草稿的行為（排除、標示或拒絕並說明）。每項附可測的 pass/fail。無法在本站窮盡者，列為指定到 domain-design 的 Open Question。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR1.1 | 建圖端點 `POST /api/collab/diagrams` 會呼叫 `_validate_diagram_payload`（`collab_router.py:239-245`），拒絕空的或不像 draw.io 的 `xml_data`；`CreateDiagramRequest` 繼承 `SaveDiagramRequest`，沒有「不帶內容」的建圖路徑。需求沒說大腦新建時送什麼 XML（空白骨架？由誰提供？是否通過 `_looks_like_diagram_xml`），FR1.5 的「多一張正式狀態的圖」也沒有說明建出來的初始內容。 | 在 FR1.1 或 Open Questions 補上：新建時使用的空白圖 XML 來源，以及它必須通過既有驗證。指定落點為 contract-design 或 domain-design。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR3.4、Open Questions OQ2 | 「使用者點選候選後大腦依該候選繼續原本請求」需要伺服器記得原始請求與待決狀態。現行 `SelectClarifyCandidatePayload.candidateId` 只有識別碼（`brain_gateway.py:1667`）。待決請求存在哪裡、斷線重連或逾時後怎麼處理，需求沒寫；OQ2 只問候選識別碼形狀與筆數。 | 補一個 Open Question（或 FR）：待決反問的原始請求保存位置與失效規則，並指定落點為 domain-design 或 contract-design。 | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > Constraints（資料表變更）、FR6.5、OQ3 | 加欄位的升級路徑寫成「`schema_rbac.sql`，或 `backend/database.py` 啟動補丁」。`schema_rbac.sql:345-348` 的註解明寫既有非空 volume 的唯一演進路徑是 `hierarchy_migration.py` 的 `_ensure_hierarchy_schema()`，`schema_rbac.sql` 只在空 volume 執行。FR6.5「既有的圖一律視為正式、舊版程式讀到新欄位不受影響」依賴非空 volume 上的預設值，現有文字沒有點出會走哪一條遷移。 | 修正 Constraints 與 OQ3，點名既有遷移路徑與 `DEPLOY.md` 的升級說明，並加一條可測 AC：已部署資料庫升級後，所有既有圖的狀態為正式。 | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > NFR2、FR2.2 | NFR2 說「新建步驟只多一次同行程的建圖呼叫」，但 FR2.2 要路由多問模型一題「是否要新圖」，會增加一次模型往返（或改動 Decisions API 的問題集），而這會直接影響 P50 ≤ 2 秒的首字延遲。需求沒說這一題是併入現有判定呼叫，還是另一次呼叫。 | 在 NFR2 或 FR2.2 寫明這一題是併入既有路由呼叫還是新增呼叫，並調整延遲預算的說法。 | Resolved (reviewer) |
| R-08 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR1.4、FR2.3 四項性質、FR3.5、FR3.6、FR5.2–FR5.4、NFR1 的「至少 10 句」 | 多項需求超出作答，屬設計者推導，卻沒有明確標示，例如冪等、點選重新驗證、候選排序、名稱邊角、新增 10 句標註集、四項 PBT 性質。部分標了「(corner)」，多數沒有來源標籤，讀者看不出哪些是使用者決定、哪些是分析者補的。「指令詞」清單也未定義，FR5.1 的測試只能靠舉例。 | 在這些需求旁標「設計者推導」，並指明可在 gate 推翻。FR5.1 補上指令詞的初版清單，或指定到 contract-design。 | Resolved (reviewer) |
| R-09 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR6.4a「專案頁架構圖計數與其他依系統統計圖的地方不計草稿」 | 「依系統統計圖的地方一律不計草稿」這句話，與兩處不可排除草稿的程式相衝突。(1) 系統刪除守衛（`hierarchy_service.py:212`）以 `UserDiagram.system_id` 計數，且 DDL 為 ON DELETE RESTRICT。(2) 預設專案連同使用者一併清除的判斷（`user_router.py:438`）。若這兩處也不計草稿，系統或專案會被判定為空而被刪除，草稿的外鍵卻擋住，結果是 DB 錯誤或孤兒資料。另外，`hierarchy_service.list_diagrams_of_system` 同時是三種需求共用的來源：FR3.2 的候選與 FR6.3a 必須包含草稿，FR6.4a 的評核與估價範圍必須排除草稿（`work_orchestrator.py` 的 `_resolve_diagram_set` 在目標為系統時會列出系統下全部的圖交辦評核），需求沒有說這支函式該怎麼區分。 | 把「不計草稿」限定在使用者可見的統計與顯示，並明寫刪除守衛與使用者清除判斷必須把草稿計入。另寫一條需求：系統層級目標展開成圖集合供評核或估價時排除草稿，候選與草稿反問時包含草稿。為這三種情形各補一個可測形式。 | New |
| R-10 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR6.2「產圖並存檔成功即轉為正式；使用者在工作區自己存檔也轉為正式」 | 「存檔」的觸發沒有界定。工作區的 draw.io 自動存檔（`WorkspacePage.tsx:269-286`，1.2 秒 debounce 後 PUT）與評核前寫回（`WorkspacePage.tsx:500`）走的是同一個 PUT。使用者只是打開一張空白草稿，自動存檔就可能把空白骨架轉成正式；評核前的寫回也會繞過 FR6.4a「草稿不得評核」。需求也沒寫架構設計 agent 的存回走哪個端點，由哪一個步驟負責轉正式。 | 明定轉正式的條件：內容與建立時的空白骨架不同，或來自產圖成功，而不是任何一次 PUT。同時寫清楚是哪一個端點或步驟執行轉換，並補一個可測案例：打開草稿、不做任何編輯，它仍是草稿。 | New |
| R-11 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR2.2 判定表第二列「系統下有圖／p ≥ t → 新建」與 FR6.3a | 作業對象是系統、系統下有未完成草稿、使用者要畫新圖時，FR2.2 的結果是新建，FR6.3a 的結果是反問。兩條都適用，沒有優先順序。表的第一列（系統下沒有圖）也沒說只有草稿算不算沒有圖。 | 寫明 FR6.3a 優先於 FR2.2，並說明「沒有圖」是否把草稿計入。 | New |
| R-12 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR7.1 | `diagram_change_records.source` 現行只允許 `brain_orchestration`，而 `record_diagram_change` 要求 `requirement_summary` 非空（`hierarchy_service.py:422-455`），既有的 `_record_change`（`work_orchestrator.py:850`）在產圖成功後也會寫一列。需求沒說「經大腦建立」要怎麼表示（沿用哪個欄位）、摘要內容是什麼，也沒說一次新建加產圖是一列還是兩列。 | 寫明「經大腦建立」的表示方式、摘要取值，以及每次新建請求的紀錄列數。 | New |
| R-13 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/requirements-analysis/requirements.md > FR1.1 | 既有建圖端點成功後會把 `current_user.last_opened_diagram_id` 設為新圖（`collab_router.py` create_diagram）。大腦在背景新建一張草稿，使用者下次打開工作區會落在這張草稿。需求沒有說明這是預期行為還是要避免。 | 在 FR1 或 Assumptions 寫明處置：接受此副作用，或新建時不更新最後開啟的圖。 | New |

> R-01 Reviewer note: FR1.3 規定建圖成功當下作業對象即切到新圖，FR6.3 規定再說一次接著畫同一張，FR6.3a 補上系統下有草稿時的反問，FR1.4 加了冪等。原缺口已補。FR6.3a 與 FR2.2 判定表的優先順序另列為新發現。

> R-02 Reviewer note: FR2.2 判定表已涵蓋「系統下沒有圖」且 p 落在不明區間，結果為新建，並標〔推導〕。FR2.3 的性質改用 t 表示，不再寫死 0.3／0.7。

> R-03 Reviewer note: FR6.4a 已逐項列出專案頁計數、評核與 WA 共編、估價綁定、分享四個消費者的處置，各有可測形式。但這條「一律排除」的範圍仍有缺口，見新發現第 1 列。

> R-04 Reviewer note: OQ5 已點名 `_validate_diagram_payload`（`collab_router.py:239-245`）會拒絕空 XML，並指派 contract-design 決定空白骨架來源。我實際讀過該函式，描述正確。

> R-05 Reviewer note: OQ6 已寫出待決請求的保存位置與失效規則未定，指派 domain-design。FR3.5 要求伺服器重新驗證候選。

> R-06 Reviewer note: Constraints 已改為只走 `hierarchy_migration._ensure_hierarchy_schema()`，並要求 `DEPLOY.md` 寫明升級方式。

> R-07 Reviewer note: NFR2 已改為同一次路由請求內多問一題、不增加模型往返，並交由 build-and-test 量測。

> R-08 Reviewer note: 分析者推導的項目已逐處標〔推導〕，FR5.1 給了指令詞初版清單，最終清單交 OQ1。

### Summary

上一輪的八項發現都已處理：作業對象切換、判定表與門檻、草稿消費者、空 XML、待決請求、升級路徑、延遲與〔推導〕標示。需求已足以讓工程開工。仍有兩項 Major 建議在核可前處理：「草稿一律排除」會誤傷系統刪除守衛與使用者清除判斷，且沒說明共用的圖集合函式如何區分用途；草稿轉正式的觸發條件沒有界定，工作區自動存檔與評核前寫回可能提前轉正式或繞過評核禁令。我判定兩項各有明確的修法，且可在 domain-design 與 contract-design 收斂，所以不阻擋，因此給 READY。
