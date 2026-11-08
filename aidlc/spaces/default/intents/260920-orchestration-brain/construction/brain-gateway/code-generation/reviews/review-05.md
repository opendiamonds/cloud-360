## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-13 | Fixed | Minor | (a) merge-blockers.md 第 19 列處置欄開頭現為「已查證，不構成合併前阻擋」，並在括號內保留原開頭「待處置」，其後 2026-10-24 查證文字未刪、與同欄一致。(b) 新增 backend/tests/test_deploy_required_secrets.py，三案以 yaml.safe_load 只讀 deploy.yml。讀碼推演 D1–D5 全紅：D1 刪缺值行使 count 為 0；D2 刪 env 行使 assertIn 失敗；D3 改 vars 使逐字比對失敗；D4 移到 if 之後使 assertLess 失敗；D5 刪說明行使 explains 為空。CHECK_LINE 與 MISSING_GUARD 逐字對得上 deploy.yml:94、:95。規格註解 @purpose、@given、@step、@pass、@story 齊全，不讀 secret 值，repo 內無 pyc。覆蓋缺口見新發現 1 |
| R-14 | Fixed | Minor | 三處更正逐一核對屬實：HEAD 版 DEPLOY.md 的「第 4.5 節」在第 2239 行，第 2238 行是空行；現行位移至 DEPLOY.md:2340，且已改指 code-summary 第八節 OPEN-GW13-6，該列確實存在於 code-summary:252；brain_gateway.py:1116 是 _log、:1117 是 _send_single_error；7a50a40^ 為 fa51564，fa51564 與 624c170 對 deploy.yml、DEPLOY.md、member-pages.spec.ts 的 sha256 前 12 碼相同。原文未刪，更正集中在新一節，舊節（:411、:437、:450）沒有就地指向更正的標記，屬可接受的 Minor |
| R-15 | Still applies | Minor | 未完成部分是 (e)：往後前端檢查的寫檔注意沒有落進 unit-test-instructions.md。conductor 以 code-summary 該節第四點為落點，足以讓讀 code-summary 與 merge-blockers 第 37 列的人看見，但不足以讓只讀 unit-test-instructions.md 的後續執行者看見（該檔第 40 行附近仍直接教 npx tsc -b）。計畫 Step 21 維持未勾如實，理由（Plan Approval 綁定、已逐位元還原）與守門行為相符。指紋時間部分：兩個 tsbuildinfo 的 mtime 為 11 月 8 日 07:08，早於本輪 code-summary 時間戳 01:21Z（本地 09:21），不是本輪寫的，無需重取 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | backend/tests/test_deploy_required_secrets.py > setUp 與三個測試 | 測試只檢查步驟的 env 與 run 內容，沒有斷言該步驟本身未被中和。有人在該步驟加上 continue-on-error: true 或 if: false，缺金鑰時部署照樣綠燈，三案卻仍全綠，這正是本檔 docstring 自述要防的「沒有檢查」。D1–D5 的突變集合沒有涵蓋這一類 | 在 setUp 補斷言：該步驟不含 if 與 continue-on-error（或值為 false），並補一個對應突變；或在 code-summary 把它記為已知未鎖住項 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/code-generation/code-summary.md > 合併前必修第 37 列 > 一、(a) 列；construction/functional-design/merge-blockers.md 第 37 列處置欄；brain-gateway/code-generation/traceability.json MB-37 note | 三處都寫「(a) 未落地、第 19 列仍為待處置」，但目前 merge-blockers.md 第 19 列已由 conductor 更正為「已查證」。這三處是寫入當下為真、現在為假的陳述；第 37 列結論仍是「待重審」，下一位讀者會誤以為矛盾仍在 | 在三處就地補記「(a) 已於 2026-11-08 由 conductor 更正，見第 19 列」，保留原文；或於重審時由 conductor 更新第 37 列 (a) 狀態 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/code-generation/code-generation-plan.md > Step 15 與 merge-blockers.md 第 19 列處置欄 | 第 19 列「已查證，不構成合併前阻擋」引用 Step 15 的查證結果，而 Step 15 在計畫內未勾。維持未勾的理由成立（外部狀態無法逐位元重驗、本輪禁用 gh），但結論所依的證據被標為未完成，兩處並列容易被讀成互相矛盾 | 第 19 列處置欄註明證據為 2026-10-24 的查證紀錄、本輪未重驗；合併前由有 gh 權限者重跑一次名稱查證後再勾 Step 15 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 收據 29 檔 shasum 比對 | 21 檔相同、8 檔變動，8 檔的收據 sha 皆等於 HEAD 版 | 與 code-summary 宣稱一致；8 檔為 deploy.yml、DEPLOY.md、LOCAL-DEV.md、requirements.txt、deploy/.env.example、render-env.sh、Sidebar.tsx、memory-page.spec.ts，皆為他單元的未提交改動 |
| 計畫勾選實算 | grep 得已勾 26、未勾 3 | 與 code-summary 宣稱一致 |
| 計畫 git diff -U0 | 除 Step 9 與 Step 15 的 [x] 改為 [ ]，以及新增六之二、六之三兩節外，內文無變動 | 符合只動勾選字元的約束 |
| Step 9 未勾理由 | Sidebar.tsx 與 memory-page.spec.ts 自收據後變動，本輪未跑前端 lint 與 tsc | 理由成立 |
| 行號與引用核對 | DEPLOY.md:2340、brain_gateway.py:1117、HEAD DEPLOY.md:2239、fa51564 對 624c170 皆屬實 | R-14 更正正確 |
| traceability.json | json.load 通過，含 MB-37 | 通過 |
| source-manifest.json | 已補列 test_deploy_required_secrets.py | 通過 |
| 測試與 validators | 依指示未執行，以讀碼推演 | 靜態判定；PyYAML 在 requirements.txt:32 |

### Summary

第 37 列 (a)(b)(c)(d) 皆落實且可核對，新測試能鎖住 OPENROUTER_API_KEY 的三個落點，勾選重判與數字屬實，故判 READY。(e) 以 code-summary 為落點對 code-summary 與 merge-blockers 的讀者足夠，對只讀 unit-test-instructions.md 的人不足，Step 21 未勾如實，R-15 仍為 Minor 並待重錄核可後落地。其餘為三項 Minor。已知限制：第 54 列兩項與 _prefetch、_write_episodic 走主連線依使用者裁決不在本輪範圍。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/brain_gateway_rules.py:436-466（scan_targets_in_utterance）；呼叫點 backend/services/brain_gateway.py:1233；測試 backend/tests/test_brain_gateway_rules.py:338 | 原句掃描在事件迴圈上同步執行，且複雜度為全部出現區間數的平方：_occurrences 允許重疊（rules.py:432 的 start = idx + 1），dominated 對每個區間掃過 all_spans（rules.py:459-462）。訊息上限是 4000 字（session_store.py:113）。已認證的使用者自建兩個系統「aa」「aaa」，再送由 a 組成的 4000 字句子，區間數約 8000，比較次數數量級 2×10^7（我推導，未執行），單次足以讓整個行程的所有 WebSocket、協作廣播與 SSE 停擺數秒；每分鐘 20 則的頻率上限擋不住持續停擺。掃描只在反問選定意圖後觸發，使用者要讓分類落到低信心才走得到，這是前提但不難。PBT 的句長只到 12 字（test_brain_gateway_rules.py:338），沒有任何上界測試。違反本檔禁令 2（事件迴圈上沒有同步重負載）的精神。 | 擇一或並用：把掃描放進 asyncio.to_thread；對區間數設上限（例如每個條目至多取前 N 個不重疊出現，或總區間數超限即視為零命中並走反問）；或改為排序後單次掃描線使複雜度降為 O(S log S)。並補一個最壞輸入（重複字元句子加前綴同名系統）的耗時或區間數上界測試。 | Resolved (reviewer) |
| R-02 | Minor | backend/services/brain_gateway.py:813-831（_handshake_and_serve） | 載入中佇列溢位的檢查不完整：conn.overflowed 只在送 ready 之前（:813）與排空迴圈每次送出之後（:828）檢查。若溢位發生在 ready 與快照各訊框的 await 期間，deliver 已 unregister 並清空 pending（:665-667），迴圈因 pending 為空而直接跳過，之後無檢查就 conn.phase = Phase.READY（:831）。結果是一條已移出登錄卻仍在服務的連線，永遠收不到扇出，且無任何訊號。需 256 則在送約 6 至 10 個快照訊框之間到達，實務上極難觸發，但行為是靜默失效而非關閉。 | 在設定 Phase.READY 之前加一次 overflowed 檢查並以 1011 關閉；補一案讓溢位發生在快照送出期間。 | Resolved (reviewer) |
| R-03 | Minor | backend/services/brain_gateway.py:954（_receive_loop 對 _dispatch_client_message 的呼叫）；:820（_snapshot_envelopes 無 try） | 接收迴圈與握手快照沒有最外層的例外保護。任何未預期例外（例如快照的 WorkItemsPayload 驗證失敗，或 _dispatch_client_message 某分支未被個別 try 包住）會一路穿出 handle()（只捕 WebSocketDisconnect，:749），由 ASGI 層以非結構化方式終止連線並記含 traceback 的 ERROR，而非 error(INTERNAL_ERROR) 加連線保留。finally 的清理本身正確（:751-772），不會洩漏佔位，所以只是行為與可觀測性問題。 | 在 _receive_loop 內對單則訊息的處理加 except Exception，轉成 error_for 的封閉表錯誤並繼續；握手階段的同類例外轉為 1011 關閉。補一案注入未預期例外，確認連線保留且 log 不含例外原文。 | Resolved (reviewer) |
| R-04 | Minor | backend/services/brain_gateway.py:778-785（hello 的 ws.receive） | 首則 hello 訊框不受 MAX_FRAME_BYTES（64 KiB）與頻率限制約束：大小檢查與 rate.admit 只在 _receive_loop 內。已認證的使用者可在 10 秒內送出 uvicorn 允許的最大訊框（預設 16 MiB，NFR13.19 明言不動 ws_max_size）再 json.loads，每使用者最多 10 條、全域 200 條。需要有效 token，風險有限，但與 NFR13.19 宣稱的入站單一訊框上限不一致。 | 在 hello 路徑套用同一個位元組上限（超過即 4400 或 1011）；或在 code-summary.md 揭露此例外。 | Resolved (reviewer) |
| R-05 | Minor | backend/services/brain_gateway.py:672-675（fanout）、:554-558（emit_turn）、:99（SEND_TIMEOUT_SEC） | 扇出對同一使用者的各連線依序 await，且每次送出最長等 10 秒。同一 key 下某個分頁卡住（未失敗、只是慢）會讓其他分頁的狀態訊息與推播延遲至多 10 秒乘以前面卡住的分頁數（上限 10 條連線）。M7 只驗證失敗不影響其他連線，沒有驗證變慢。範圍僅限同一使用者，且 U12 的 dispatch 也在等這個 sink。 | 在 code-summary.md 揭露此行為；或以 asyncio.gather 並行送出（每連線順序由 send_lock 保證）。補一案：一條連線的 send_text 卡住時，第二條連線仍在秒級收到訊息。 | Resolved (reviewer) |
| R-06 | Minor | backend/services/brain_gateway.py:1237-1240；code-summary.md 偏離 D6 | 偏離 D6 如實揭露且理由合理，但它確實讓帶入項 28 的字面要求（掃描零命中不得靜默交辦舊對象）在專案 > 50 且已選定專案時失效：使用者點名了另一個專案的系統，因目錄截斷而不在候選內，掃描零命中，直接交辦給目前選定的專案。高信心路徑（:1261）對同一情境回專案太多，兩條路徑行為不一致。code-summary.md 自己寫請核可，本次審查不代替人工核可。 | 閘門上請使用者明確核可或否決 D6；若核可，在 U14 交接表與 functional-spec.md 回補註明這個殘留，並補一案鎖住已選定專案、截斷、零命中則交辦的行為，使其成為有意的決定而非巧合。 | Resolved (reviewer) |
| R-07 | Minor | deploy/render-env.sh:21；.github/workflows/deploy.yml:76-83、91-93 | render-env.sh 檔頭仍寫 OPENROUTER_API_KEY optional（empty disables generation），而同一個 PR 已讓 deploy.yml 的必要 secret 檢查把它列為必要，DEPLOY.md:24 與 deploy/.env.example 也已改。該腳本刻意不檢查（讓回滾可 render）是對的，但檔頭註解現在與 workflow 矛盾，下一位維護者讀 render-env.sh 會得到相反結論。code-summary.md 的取代關係表也未列這一處。 | 在 render-env.sh 檔頭該行補註 staging 部署由 deploy.yml 強制必要、此腳本接受空值僅為讓 rollback 可 render，並同步 code-summary.md。 | Resolved (reviewer) |
| R-08 | Minor | backend/services/brain_gateway.py > `_end_turn`（:1230-1254）與 `_on_unexpected`（:1148-1154） | T9 以 `turn.ledger.is_terminal` 判斷「該輪已終止」，但這是帳本狀態，不等於客戶端已收到終止事件。`_end_turn` 在 :1230 先呼叫 `ledger.finish()` 把狀態設為 DONE，之後才組 `done` envelope 並 `conn.send`（:1254）。若 finish() 與 send 之間拋出未預期例外（例如 `self.envelope` 序列化），T9 看到終止態，改送 turnId=null 的錯誤，該輪永遠收不到終止事件，與 T9 要修的缺口同形。視窗很窄（歷史寫入已被 try/except 包住），不阻擋。我沒有找到並行任務競爭帳本的路徑：`fail()` 與 `finish()` 都在單一事件迴圈內同步改狀態，不會重複終止。`open_turn` 只由接收迴圈讀寫（全樹 grep 僅 `brain_gateway.py`），`spawn` 的背景任務與 `emit_turn`（自帶獨立 turnId 與帳本）都不碰它，不會跨訊息或跨任務殘留。 | 在 code-summary 揭露這個視窗，或把 `finish()` 之後到送出 `done` 之間的步驟包進同一個保護，使「帳本終止」與「終止事件已送出」一致。 | Resolved (reviewer) |
| R-09 | Minor | backend/tests/test_brain_gateway_turn.py:990 與 :999-1060（T9 三案） | 測試替身拋出 `RuntimeError("SECRET-MARKER unexpected")`，但 T9 三案都沒有斷言錯誤訊息或 log 不含該標記（同檔 :537、handshake :211 的其他案例才有 `assertNotIn`）。若有人把 T9 分支改成回送 `str(exc)`，這三案不會紅，M1–M5 突變也涵蓋不到。 | 在 T9 輪內案與 after_select 案加上 `assertNotIn("SECRET-MARKER", json.dumps(err))`，讓標記真的發揮作用。 | Resolved (reviewer) |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/code-generation/code-generation-plan.md > §六 規則表 T1–T9 的行號 | 計畫表內的行號是修改前的值，與現行程式不符：T1 寫 `:1088`／`:1092`／`:1102`（實為 :1091／:1095／:1105）、T3 寫 `:1126`（實為 :1131）、T4 寫 `:1166`（實為 :1192）、T5 寫 `:1531`（實為 :1558）、T6 寫 `:1541`（實為 :1568）、T9 寫 `:1130-1132`（實為 :1136-1138）。code-summary §13.1 的行號我逐一核對過是對的（:1113、:1131、:1142、:233、:1276、:1562、:1133、:1140），只有計畫表過期。 | 在計畫表加註「行號為修改前」，或以 code-summary §13.1 的行號為準，避免後續讀者照計畫的行號找不到對應程式。 | Resolved (reviewer) |
| R-11 | Minor | backend/services/brain_gateway.py:1560-1569（`_on_select`）對照 :1129-1132（T3） | `[GW-MB2]`=A 的理由是「使用者可重選」，所以格式錯誤的選擇保留反問。但格式正確、id 不在候選內的選擇（T6）在 :1560 已先清掉 `pending_clarify`，:1568 再結束該輪，之後使用者無法重選，只能重新說一句。表上標示 T6「現行不變」，行為與規則表一致，只是同一個「選錯」情境兩種結局。 | 在 code-summary §13.1 明寫 T6 與 T3 的差異是刻意的（還是未決），讓閘門上的人知道。 | Resolved (reviewer) |
| R-12 | Minor | frontend/src/brain/useBrainConnection.ts:173-184 與 frontend/src/brain/brainTranscript.ts:289-292（跨單元整合點，屬 entry-page-ui） | 本單元合併後（deploy-on-merge），伺服器會對 T1–T5、T7、T9 的非輪內分支送 turnId=null 的 error。現行前端把 null 轉成空字串輪次，reducer 的 `error` 分支會 `clearPending(resolvePicking(...))`，且 :183 `setAwaitingReply(false)`。所以 `[GW-MB2]`=A「反問保留、可重選」在伺服器端成立，畫面端要等 merge-blockers 第 2 列 (b) 完成才一致。這點已在 code-summary §13.5 與 merge-blockers 揭露，但沒有記錄合併順序約束。我只讀了前端現況，沒有在瀏覽器驗證實際畫面。 | 在 merge-blockers 第 2 列記明：(b) 須與本單元同批合併，或接受兩者之間的過渡行為。 | Resolved (reviewer) |
| R-13 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md > 第 19 列狀態欄；backend/tests（無對應測試）；.github/workflows/deploy.yml:83 | 第 19 列狀態欄開頭仍寫「待處置」，其後卻寫「已查證、不構成阻擋」，兩者矛盾。另外 deploy.yml:83 的必要 secret 檢查含 `OPENROUTER_API_KEY`，但沒有任何測試斷言這一點（backend/tests 中提到該名稱的檔案皆與部署檢查無關），日後有人刪掉該行不會有任何紅燈，而後果是缺金鑰時 deploy 失敗並觸發自動 rollback 與 revert PR。code-summary 重做段已自行揭露這兩點，本次確認屬實。 | 把第 19 列狀態欄開頭改為已處置；補一個讀取 deploy.yml 並斷言必要 secret 檢查含 `OPENROUTER_API_KEY` 的小測試，或在 code-summary 明記這是已知未鎖住項並指定承接。 | Unresolved |
| R-14 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/code-generation/code-summary.md > 共用檔異動後的重新驗證與補審 > 第一節 DEPLOY.md 段、第四節 L3、第三節 R-10 列、收據段 | 補審節有三處引用差一或不準，而 L3 是要交給 conductor 抄進 merge-blockers 的：(1) 懸空引用「U13 code-summary 第 4.5 節」實際在 DEPLOY.md 第 2239 行（我 grep 與 sed 核對），摘要寫 2238（第 2238 行是空行）；同段「現行 2229、2238」亦同。(2) R-10 列寫 T2 錯誤送出在 `:1116`，該行是 `_log(... revalidate_failed ...)`，`_send_single_error` 在 `:1117`。(3) 寫「`7a50a40^`（＝`624c170`）」，實際 `7a50a40^` 是 `fa51564`；不過 624c170 與 fa51564 對這三檔內容相同（git diff --stat 為空），所以結論不受影響 | 就地更正這三處為 DEPLOY.md:2239、`:1117`、`7a50a40^` 即 `fa51564`（內容與 `624c170` 對這三檔相同）；L3 併入 merge-blockers 前先用更正後的行號 | New |
| R-15 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/code-generation/code-summary.md > 共用檔異動後的重新驗證與補審 > 第二節「偏離」 | 開發者自承 `tsc -b` 在副本跑時因 node_modules 為指回 repo 的 symlink，改寫了 repo 內 `frontend/node_modules/.tmp/tsconfig.app.tsbuildinfo` 與 `tsconfig.node.tsbuildinfo`。我核對：兩檔 mtime 為今日 10:55，`git check-ignore` 命中 `frontend/.gitignore:10`，`git status` 排除 aidlc 後無任何受版控檔異動，所以不影響任何版控檔，也不影響本輪結論（lint、check:ws-types 我在 repo 內以唯讀方式重跑，結果相同）。但依專案規則，引擎的來源指紋會把被忽略的建置快取算進去；本次審查請求的指紋若是在該改寫之前取得，會與現況不符而使收據失效 | 不需改程式。請 conductor 確認本次審查請求的指紋取得時間晚於 10:55；若早於，需判斷是否重取。往後前端檢查改用實體複製 node_modules 或 `--tsBuildInfoFile` 指向副本，並把此作法寫進 unit-test-instructions.md 第二節現況註記 | New |

> R-13 Not re-checked this round

> R-14 Not re-checked this round

> R-15 Not re-checked this round
