## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-12T16:33:19Z
**Iteration:** 1

### Findings

| ID | Severity | Status | Location | Finding | Required action |
|---|---|---|---|---|---|
| R-01 | Major | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR64.9 logic (:372-375); functional-spec.md > 2.2 match_referent (:47) | 修正 review-01 R-01 引入的新缺口：AC1.1.5 的 Given 是「脈絡列顯示尚未選定」（inception/user-stories/stories.md:43），但 BR64.9 只在「當前段已選專案下」比對系統名稱，再比對專案名稱。尚未選定時沒有已選專案，系統名稱永遠無法解析；而 HierarchyFacade.list_systems 必須帶 project_id（backend/services/hierarchy_facade.py:282）。結果：使用者在未選定狀態說「把訂單系統的圖加一個快取」，系統走 BR64.11(b) 回「找不到名為訂單系統的系統或專案」並不交辦，AC1.1.5 的主情境（系統名稱、未選定）在本設計下不可達。review-01 R-01 列的「系統不在已選專案下」情境同樣落入零筆。traceability 把 AC1.1.5 記為 N/A（屬 US1），所以沒有任何一列會揭露此落差。 | 明確定義系統名稱的搜尋範圍（例如對使用者可見的每個專案各 list_systems，彙整後做 casefold 比對，並寫明呼叫次數上限與失敗處置），或明文把「僅專案名稱可解析」記為對 AC1.1.5 的收窄並回報上游由使用者裁決；補一個「未選定且系統名稱唯一存在於某專案」的測試案例；在 traceability 或 OPEN 項中指名 AC1.1.5 的承接。 |
| R-02 | Major | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/functional-spec.md > GW-W3 第三列 (:162); rules.md > BR64.8 (:360) | 反問後選定意圖的路徑仍會靜默對舊作業對象交辦（review-01 R-01 的同類缺陷在另一入口殘留）。低於門檻時 U11 的 decide() 保證 intents 為空（backend/services/intent_routing_predicate.py:253-274），公開的 ClarifyCandidate 只有 id、label、capability、confidence（backend/services/intent_routing_types.py:54-65 區段），不帶 referent。BR64.8 以 Intent(候選.capability, None) 組判定，GW-W3 並明寫「不再解析 referent，候選無 referent」。使用者若說「把訂單系統那張圖弄一下」而分類信心不足，選定解讀後 referent 已不存在，dispatch 在舊作業對象或未選定的狀態上建立工作項，畫面無提示。BR64.11 的『不得帶舊對象交辦』因此只涵蓋高信心路徑。 | 為此路徑定義處置：例如在選定後以本單元自己的名稱比對對 utterance 再解析一次（需先解 R-01），或在作業對象與使用者句中名稱不一致時一律要求指定，或回到 U11 要求 ClarifyCandidate 帶 referent（需契約修訂並列入 OPEN-GW13-1）。補規則、補測試，並更正 GW-W3 的假設。 |
| R-03 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/functional-spec.md > GW-W1 步驟 7 至 9 (:84-100 區段); rules.md > BR63.1、BR63.2 | 握手期有兩個檢查後行動的競態：load 與 list_items（步驟 7）發生在登錄（步驟 8）之前，這段時間內另一分頁的 set_work_target 或 U12 的 emit_session 扇出看不到本連線，而步驟 9 推送的是登錄前取得的舊快照，客戶端會停在舊狀態直到下一次狀態改變。即使登錄後，步驟 9 的舊快照也可能在較新的扇出訊息之後才送出。review-01 R-05 的修正把 load 移到 ready 之前，同時放大了這個窗口。 | 改為先登錄再讀取推送，或在登錄後重讀一次並以版本比對決定是否補送；在 BR63.2 寫明快照與扇出的排序保證，並補一個「讀取期間發生狀態改變」的測試。 |
| R-04 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/functional-spec.md > 十一之一 C-1 與 十一之二 第 5 點 (:210-235 區段) | 契約增量對既有測試的衝擊被低估：C-1 把必填的 protocolName 加進 WsSubprotocol，但 backend/tests/test_ws_contract.py:283、:288、:290 以只含 scheme 與 separator 的方式構造該模型，加欄位後三處會直接驗證失敗；同檔 :61-62 的 sharing_mode 與 work_target 樣本缺 scope 與 segment，C-3、C-4 合入後會使逐型別樣本測試失敗。步驟 5 只寫「若斷言欄位集合」，並未指出這些具體破點。另 WsSubprotocol 是格式描述模型而非實際訊息，必填屬性對它的語意（伺服器從不構造它）未交代。 | 在十一之二列出必須同步修改的測試位置與新增的 C-1 斷言寫法（沿用該檔以 get_args 取字面值的形狀）；說明 WsSubprotocol.protocolName 是否真的需要成為模型欄位，或改以獨立常數加字面型別承載。 |
| R-05 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR64.11 (a) 與 (b)(c) 末句 (:393-409) | 兩處不精確：其一，(a) 的候選 capability 取「本輪意圖的 capability」，但 BR64.9 允許多個意圖共用同一 referent，多意圖且 capability 不同時單一 capability 欄位無法表達，client 也無法分辨這是 target 反問而非 intent 反問（ClarifyPayload 無鑑別欄位，backend/services/brain_ws_contract.py:214-226）。其二，(b)(c)「不寫 episodic 以外的任何狀態」語意含糊，且與 BR67.7（以 done 結束且非攔截者寫 episodic）相互作用未說明：這兩種固定句型是否寫 episodic 無法判定。 | (a) 規定多意圖時的候選構成與 capability 取值，並確認 U14 以 label 區分即足夠；(b)(c) 明寫是否寫 episodic，並把句子改為可測的陳述。 |
| R-06 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR67.11 (:635-650); functional-spec.md > GW-W7 (:184-189) 與 A-6 | startup 建立元件的規格不完整：其一，順序只寫在 configure_session_env 與 configure_embedding_env 之後，但 IntentRouter 建構子會呼叫 resolve_routing_config（backend/services/intent_routing.py:340 起），必須排在 configure_intent_routing_env 之後，且現行 main.py:55-83 的 hook 尾端才是 init_db，位置未定。其二，SessionStore 需要 RedisGateway 的 client，未指名由哪些環境變數經 build_redis_client 建立（backend/services/redis_gateway.py:510-536 要求 url、user、password 並拒絕 default 使用者），也未定缺值時是否啟動失敗。A-6 的連線時機其實可由此函式檢視確定（ConnectionPool 與 Redis 皆延遲連線），不必留給 code-generation 確認。 | 在 GW-W7 寫明完整的建立順序與 Redis client 的設定來源及失敗語意，並把 A-6 改為已確認的事實；變更 .env.example 或 render-env.sh 時須同步 LOCAL-DEV.md（project.md 規則）。 |
| R-07 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR67.10 與 BR67.5 | 預取把事件迴圈阻塞轉成執行緒池壓力：asyncio.to_thread 使用共用的預設執行緒池，Ollama 不可用時每則入口頁訊息佔用一條執行緒至多 10 秒（backend/services/embedding_port.py 逾時預設），而同一個池也承載認證、session load、重驗與所有其他 to_thread 呼叫。少數並行的慢嵌入即可讓全部連線的認證與讀取排隊，BR67.10 的可驗證性測試只量測迴圈排程延遲，量不到這個失效模式。 | 為預取指定獨立且有上限的執行器或並行信號量，並加上失敗後的短期快速失敗（避免每則訊息都重付逾時）；測試補一個「慢嵌入並行時 load 與認證仍在預算內完成」的案例，或明列為已知殘留。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 規則數與追溯覆蓋（YAML 與正規式解析 rules.md 對 traceability.json） | PASS：49 條規則、49 個不重複 ID，每條都出現在 coverage 或 reverse，無懸空 id | 與 spec 宣稱的 49 一致 |
| traceability 狀態集合（.claude/sensors/aidlc-traceability.md:56） | PASS：Deferred 屬合法狀態且要求非空 target | AC8.1.1 標 Deferred 誠實：target 與 note 如實記載無逐字內容來源，與 U12 固定句型實況相符 |
| review-01 R-01 複驗 | 部分修好：BR64.11 補上三種失敗分支且不再宣稱由 U12 處理，但範圍與入口仍有缺口 | 缺口記為本輪 R-01、R-02 |
| review-01 R-02 複驗 | 已依使用者裁決處理：AC8.1.1 Deferred、OPEN-GW13-15、A-4、BR65.2 一致 | 不再有恆真的 OK 宣稱 |
| review-01 R-03 複驗 | 已修好：BR67.10 預取加 ContextVar；實測 classify 內 fetch_routing_context 在同一協程直接呼叫 search（intent_routing.py:451-456 區段），ContextVar 可見；_memory_notes 會捕獲轉接器拋出的例外並降級（intent_routing.py:192-235） | 介面與呼叫時機相符；殘留為本輪 R-07 |
| review-01 R-04 複驗 | 大致修好：C-1 至 C-6 逐欄列出型別、必填、預設、閘門步驟與撰寫者；dump_ws_contract.py:108-116 白名單位置正確；--check 與 npm 閘門步驟可行 | 測試衝擊低估為本輪 R-04；舊客戶端相容僅 DEMO 頁，已列入 OPEN-GW13-10 |
| review-01 R-05 至 R-12 複驗 | R-05、R-06、R-07、R-08、R-09、R-10、R-11、R-12 皆已修入（握手時點、PBT 定義域、BR62.1 與 BR62.6、先讀後寫、BR65.5、H-24 與 BR67.8、AC8.1.3 兩案例、BR67.11） | R-12 的新增細節缺口為本輪 R-06；R-05 修正附帶的競態為本輪 R-03 |
| 行號抽查（main.py:55-83 startup hook、auth.py:58-84 get_user_from_token record 參數、hierarchy_facade.py:282 list_systems、intent_routing.py:192-235、brain_ws_contract.py:214 與 :410、dump_ws_contract.py:108-116、redis_gateway.py:510） | PASS：內容與定位皆相符 | 本輪新增引用可信 |
| 他單元抽查 | 未執行 | reviewer-scope 掛鉤禁止開啟兄弟單元，U10、U12 細節僅依本單元文件與已交付程式判斷 |
| 測試 | 未執行 | 依派工指示不跑測試 |

### Summary

Critical 0、Major 2、Minor 5，判定 NOT-READY（有未解的 Major）。新發現來源分類：修正新引入 2（R-01 的比對範圍是 BR64.9/BR64.11 修正引入的新缺口，R-03 是 review-01 R-05 把 load 移到 ready 之前所放大的競態）、既存漏審 3（R-02 的反問後選定路徑、R-04 的測試衝擊、R-07 的執行緒池壓力）、新設計問題 2（R-05、R-06）。最重的問題是 referent 解析在 AC1.1.5 的主情境（未選定加系統名稱）下不可達，以及低信心反問後選定的路徑仍會靜默對舊作業對象交辦；其餘 review-01 項目（記憶預取、契約增量、握手分界、重驗、啟動建立）皆已實質修好，介面與呼叫時機與已交付程式相符。
