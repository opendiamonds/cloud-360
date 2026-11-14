## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-24T03:18:48Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/brain_gateway_rules.py:436-466（scan_targets_in_utterance）；呼叫點 backend/services/brain_gateway.py:1233；測試 backend/tests/test_brain_gateway_rules.py:338 | 原句掃描在事件迴圈上同步執行，且複雜度為全部出現區間數的平方：_occurrences 允許重疊（rules.py:432 的 start = idx + 1），dominated 對每個區間掃過 all_spans（rules.py:459-462）。訊息上限是 4000 字（session_store.py:113）。已認證的使用者自建兩個系統「aa」「aaa」，再送由 a 組成的 4000 字句子，區間數約 8000，比較次數數量級 2×10^7（我推導，未執行），單次足以讓整個行程的所有 WebSocket、協作廣播與 SSE 停擺數秒；每分鐘 20 則的頻率上限擋不住持續停擺。掃描只在反問選定意圖後觸發，使用者要讓分類落到低信心才走得到，這是前提但不難。PBT 的句長只到 12 字（test_brain_gateway_rules.py:338），沒有任何上界測試。違反本檔禁令 2（事件迴圈上沒有同步重負載）的精神。 | 擇一或並用：把掃描放進 asyncio.to_thread；對區間數設上限（例如每個條目至多取前 N 個不重疊出現，或總區間數超限即視為零命中並走反問）；或改為排序後單次掃描線使複雜度降為 O(S log S)。並補一個最壞輸入（重複字元句子加前綴同名系統）的耗時或區間數上界測試。 | New |
| R-02 | Minor | backend/services/brain_gateway.py:813-831（_handshake_and_serve） | 載入中佇列溢位的檢查不完整：conn.overflowed 只在送 ready 之前（:813）與排空迴圈每次送出之後（:828）檢查。若溢位發生在 ready 與快照各訊框的 await 期間，deliver 已 unregister 並清空 pending（:665-667），迴圈因 pending 為空而直接跳過，之後無檢查就 conn.phase = Phase.READY（:831）。結果是一條已移出登錄卻仍在服務的連線，永遠收不到扇出，且無任何訊號。需 256 則在送約 6 至 10 個快照訊框之間到達，實務上極難觸發，但行為是靜默失效而非關閉。 | 在設定 Phase.READY 之前加一次 overflowed 檢查並以 1011 關閉；補一案讓溢位發生在快照送出期間。 | New |
| R-03 | Minor | backend/services/brain_gateway.py:954（_receive_loop 對 _dispatch_client_message 的呼叫）；:820（_snapshot_envelopes 無 try） | 接收迴圈與握手快照沒有最外層的例外保護。任何未預期例外（例如快照的 WorkItemsPayload 驗證失敗，或 _dispatch_client_message 某分支未被個別 try 包住）會一路穿出 handle()（只捕 WebSocketDisconnect，:749），由 ASGI 層以非結構化方式終止連線並記含 traceback 的 ERROR，而非 error(INTERNAL_ERROR) 加連線保留。finally 的清理本身正確（:751-772），不會洩漏佔位，所以只是行為與可觀測性問題。 | 在 _receive_loop 內對單則訊息的處理加 except Exception，轉成 error_for 的封閉表錯誤並繼續；握手階段的同類例外轉為 1011 關閉。補一案注入未預期例外，確認連線保留且 log 不含例外原文。 | New |
| R-04 | Minor | backend/services/brain_gateway.py:778-785（hello 的 ws.receive） | 首則 hello 訊框不受 MAX_FRAME_BYTES（64 KiB）與頻率限制約束：大小檢查與 rate.admit 只在 _receive_loop 內。已認證的使用者可在 10 秒內送出 uvicorn 允許的最大訊框（預設 16 MiB，NFR13.19 明言不動 ws_max_size）再 json.loads，每使用者最多 10 條、全域 200 條。需要有效 token，風險有限，但與 NFR13.19 宣稱的入站單一訊框上限不一致。 | 在 hello 路徑套用同一個位元組上限（超過即 4400 或 1011）；或在 code-summary.md 揭露此例外。 | New |
| R-05 | Minor | backend/services/brain_gateway.py:672-675（fanout）、:554-558（emit_turn）、:99（SEND_TIMEOUT_SEC） | 扇出對同一使用者的各連線依序 await，且每次送出最長等 10 秒。同一 key 下某個分頁卡住（未失敗、只是慢）會讓其他分頁的狀態訊息與推播延遲至多 10 秒乘以前面卡住的分頁數（上限 10 條連線）。M7 只驗證失敗不影響其他連線，沒有驗證變慢。範圍僅限同一使用者，且 U12 的 dispatch 也在等這個 sink。 | 在 code-summary.md 揭露此行為；或以 asyncio.gather 並行送出（每連線順序由 send_lock 保證）。補一案：一條連線的 send_text 卡住時，第二條連線仍在秒級收到訊息。 | New |
| R-06 | Minor | backend/services/brain_gateway.py:1237-1240；code-summary.md 偏離 D6 | 偏離 D6 如實揭露且理由合理，但它確實讓帶入項 28 的字面要求（掃描零命中不得靜默交辦舊對象）在專案 > 50 且已選定專案時失效：使用者點名了另一個專案的系統，因目錄截斷而不在候選內，掃描零命中，直接交辦給目前選定的專案。高信心路徑（:1261）對同一情境回專案太多，兩條路徑行為不一致。code-summary.md 自己寫請核可，本次審查不代替人工核可。 | 閘門上請使用者明確核可或否決 D6；若核可，在 U14 交接表與 functional-spec.md 回補註明這個殘留，並補一案鎖住已選定專案、截斷、零命中則交辦的行為，使其成為有意的決定而非巧合。 | New |
| R-07 | Minor | deploy/render-env.sh:21；.github/workflows/deploy.yml:76-83、91-93 | render-env.sh 檔頭仍寫 OPENROUTER_API_KEY optional（empty disables generation），而同一個 PR 已讓 deploy.yml 的必要 secret 檢查把它列為必要，DEPLOY.md:24 與 deploy/.env.example 也已改。該腳本刻意不檢查（讓回滾可 render）是對的，但檔頭註解現在與 workflow 矛盾，下一位維護者讀 render-env.sh 會得到相反結論。code-summary.md 的取代關係表也未列這一處。 | 在 render-env.sh 檔頭該行補註 staging 部署由 deploy.yml 強制必要、此腳本接受空值僅為讓 rollback 可 render，並同步 code-summary.md。 | New |
| R-08 | Minor | backend/services/brain_gateway.py > `_end_turn`（:1230-1254）與 `_on_unexpected`（:1148-1154） | T9 以 `turn.ledger.is_terminal` 判斷「該輪已終止」，但這是帳本狀態，不等於客戶端已收到終止事件。`_end_turn` 在 :1230 先呼叫 `ledger.finish()` 把狀態設為 DONE，之後才組 `done` envelope 並 `conn.send`（:1254）。若 finish() 與 send 之間拋出未預期例外（例如 `self.envelope` 序列化），T9 看到終止態，改送 turnId=null 的錯誤，該輪永遠收不到終止事件，與 T9 要修的缺口同形。視窗很窄（歷史寫入已被 try/except 包住），不阻擋。我沒有找到並行任務競爭帳本的路徑：`fail()` 與 `finish()` 都在單一事件迴圈內同步改狀態，不會重複終止。`open_turn` 只由接收迴圈讀寫（全樹 grep 僅 `brain_gateway.py`），`spawn` 的背景任務與 `emit_turn`（自帶獨立 turnId 與帳本）都不碰它，不會跨訊息或跨任務殘留。 | 在 code-summary 揭露這個視窗，或把 `finish()` 之後到送出 `done` 之間的步驟包進同一個保護，使「帳本終止」與「終止事件已送出」一致。 | New |
| R-09 | Minor | backend/tests/test_brain_gateway_turn.py:990 與 :999-1060（T9 三案） | 測試替身拋出 `RuntimeError("SECRET-MARKER unexpected")`，但 T9 三案都沒有斷言錯誤訊息或 log 不含該標記（同檔 :537、handshake :211 的其他案例才有 `assertNotIn`）。若有人把 T9 分支改成回送 `str(exc)`，這三案不會紅，M1–M5 突變也涵蓋不到。 | 在 T9 輪內案與 after_select 案加上 `assertNotIn("SECRET-MARKER", json.dumps(err))`，讓標記真的發揮作用。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/code-generation/code-generation-plan.md > §六 規則表 T1–T9 的行號 | 計畫表內的行號是修改前的值，與現行程式不符：T1 寫 `:1088`／`:1092`／`:1102`（實為 :1091／:1095／:1105）、T3 寫 `:1126`（實為 :1131）、T4 寫 `:1166`（實為 :1192）、T5 寫 `:1531`（實為 :1558）、T6 寫 `:1541`（實為 :1568）、T9 寫 `:1130-1132`（實為 :1136-1138）。code-summary §13.1 的行號我逐一核對過是對的（:1113、:1131、:1142、:233、:1276、:1562、:1133、:1140），只有計畫表過期。 | 在計畫表加註「行號為修改前」，或以 code-summary §13.1 的行號為準，避免後續讀者照計畫的行號找不到對應程式。 | New |
| R-11 | Minor | backend/services/brain_gateway.py:1560-1569（`_on_select`）對照 :1129-1132（T3） | `[GW-MB2]`=A 的理由是「使用者可重選」，所以格式錯誤的選擇保留反問。但格式正確、id 不在候選內的選擇（T6）在 :1560 已先清掉 `pending_clarify`，:1568 再結束該輪，之後使用者無法重選，只能重新說一句。表上標示 T6「現行不變」，行為與規則表一致，只是同一個「選錯」情境兩種結局。 | 在 code-summary §13.1 明寫 T6 與 T3 的差異是刻意的（還是未決），讓閘門上的人知道。 | New |
| R-12 | Minor | frontend/src/brain/useBrainConnection.ts:173-184 與 frontend/src/brain/brainTranscript.ts:289-292（跨單元整合點，屬 entry-page-ui） | 本單元合併後（deploy-on-merge），伺服器會對 T1–T5、T7、T9 的非輪內分支送 turnId=null 的 error。現行前端把 null 轉成空字串輪次，reducer 的 `error` 分支會 `clearPending(resolvePicking(...))`，且 :183 `setAwaitingReply(false)`。所以 `[GW-MB2]`=A「反問保留、可重選」在伺服器端成立，畫面端要等 merge-blockers 第 2 列 (b) 完成才一致。這點已在 code-summary §13.5 與 merge-blockers 揭露，但沒有記錄合併順序約束。我只讀了前端現況，沒有在瀏覽器驗證實際畫面。 | 在 merge-blockers 第 2 列記明：(b) 須與本單元同批合併，或接受兩者之間的過渡行為。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 指定的 8 個測試模組（`unittest`，`PYTHONDONTWRITEBYTECODE=1`、`HYPOTHESIS_STORAGE_DIRECTORY` 在 scratchpad） | Ran 141 tests, OK (skipped=1) | 與 code-summary §13.2 的 141 案相符 |
| `shasum -a 256 backend/services/brain_gateway.py` | `49748a71…c13b3` | 與 §13.3 的修改後基線相同，審查期間未改動來源 |
| `gh api …/actions/secrets` 與 `…/variables`（唯讀，只取名稱索引） | secrets 共 13 個、含 `OPENROUTER_API_KEY`；variables 共 2 個、不含 | 與 §13.4 相符，Step 15 可重現 |
| `grep -c "_send_single_error(conn"`（逐行核對） | 13 處呼叫（:1113、1131、1154、1165、1192、1527、1558、1602、1616、1619、1633、1636、1661） | 與 §13.1 的 13 處相符 |
| AST 結構測試 `test_mint_turn_id_only_where_a_turn_really_opens` | 通過；`_mint_turn_id` 只出現在 `_on_user_message`（:1275）與 `emit_turn`（:554） | T1–T5、T7 不再捏造 turnId |

### Summary

T1–T9 每一列都能在呼叫點對上程式，T9 與 TurnLedger 的 `fail()`／`finish()` 都在單一事件迴圈內同步改狀態，我沒有找到重複終止或 `open_turn` 洩漏的路徑，141 案與 code-summary 的數字、突變敘述一致。以上五項皆為 Minor，不阻擋核可。其中最值得閘門上確認的是 T9 的「帳本終止 ≠ 客戶端已收到終止事件」窗口，以及前端 (b) 的合併順序。
