## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-05 | Still applies | Minor | brain_gateway.py 第 909 行仍直接 await self._names_for，該方法第 995 行起以 asyncio.to_thread 執行，無 GatewayTiming.wait_for 逾時（本檔內 wait_for 只出現在 timing 相關位置）。前端 useBrainConnection.ts 的 setTimeout 只有第 355 行的重連退避，awaiting-ready 無逾時。檔案與收據逐位元相同，未變。維持 Minor，已在 code-summary 第六節列為已知限制待併入 merge-blockers。 |
| R-06 | Still applies | Minor | test_brain_gateway_limits.py 第 80 至 82 行仍以 while total_slots 等待、逾時後不斷言槽位為 0。該檔屬 brain-gateway，不在本單元來源清單內。 |
| R-13 | Still applies | Minor | unit-test-instructions.md 第 23、24、28、39、46、47、192 行仍寫 python scripts，第 75、76 行為 python3。依計畫第十一節該檔不得改，code-summary 第三節已補記以 python3 代 python。 |
| R-14 | Still applies | Minor | code-summary.md 第十六之二至之四標題下仍無就地註記；第 367、379 行與第三節已說明舊語意被 EP-R2 取代。僅為紀錄可讀性問題。 |
| R-15 | Still applies | Minor | deploy.yml 第 43 行 output 語意仍無真實失敗 run 觀察。DEPLOY.md 內未見尚未在真實失敗 run 上觀察之類的註記。code-summary 已列為交 build-and-test 的未驗證項。 |
| R-16 | Still applies | Minor | DEPLOY.md 以後續合併、連續、尚未在真實搜尋 0 命中，5.13 仍未補未裁決前後續合併會重複在 6a 失敗與環境性對程式性的判準。已列為已知限制。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/code-generation/code-summary.md > 整站重跑後的勾選回復 > 依據 | 本單元目錄下有兩份同為 2026-11-08 14:23:02 的收據：reviewed-source-5bac9ccd7b33.tsv 與 reviewed-source-86762ca52dcc.tsv，內容差 7 個檔。我獨立重算，5bac 對現況 53 同、0 變；86762 為 46 同、7 變（即前一輪回歸節所述的 7 個變動檔）。code-summary 新節用的是 5bac，與重算相符，但沒有說明另一份 86762 為何仍在、也沒說明哪一份才是本輪 REVIEW_REQUESTED 的基準。 | 在 code-summary 補一句說明 86762 是上一輪回歸前的舊收據、5bac 為審查後的對照基準，避免後續讀者誤用較舊的一份而得出 7 個變動的結論。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/code-generation/code-generation-plan.md > 第 291 行與 Step 23（第 514 行）未勾格 | 兩個未勾格的理由仍成立：第 291 行需對 compose stack 跑 6a 正案與突變 D1，從未執行；Step 23 的唯一真實 stack 證據是 run 40423381616（head c6a40f9），早於 Sidebar.tsx、ContextBar.tsx、deploy.yml 的後續改動，而 CI run 42454550208 不含 ui-regression，因此仍無現況下 entry-page-live、regression、estimate-workspace 三檔的綠燈。這是已揭露的限制，非新缺陷。 | 不需勾選。維持交 build-and-test 或下一次 ui-regression 承擔，不要在取得真實 run 前宣稱已驗。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum -a 256 -c 對 reviewed-source-5bac9ccd7b33.tsv（awk 以 tab 取欄位） | 53 OK、0 FAILED | 與 conductor 所述一致，本單元來源檔自該收據後逐位元相同，後續 commit 33deb2e 與其他單元變動未碰到本單元清單內的檔 |
| shasum -a 256 -c 對 reviewed-source-86762ca52dcc.tsv | 7 FAILED（deploy.yml、DEPLOY.md、hierarchy_facade.py、membership_facade.py、test_hierarchy_service.py、Sidebar.tsx、ContextBar.tsx） | 為較舊的收據，與前一輪回歸節的 46／7 吻合，非本輪新變動 |
| git diff HEAD 對 code-generation-plan.md | 無任何差異 | 計畫內文與勾選皆與 HEAD 相同，未動內文 |
| grep 勾選數 | 已勾 57、未勾 2（第 291、514 行） | 與 code-summary 新節自述屬實 |
| git diff HEAD 對本單元目錄 | 僅 code-summary.md 追加 8 行、code-generation-questions.md 的兩個引擎指紋行 | 新節為純追加；指紋行屬引擎重跑產物，非人為改寫 |

### Summary

本單元來源檔與審查收據逐位元相同，計畫與 HEAD 無差異，code-summary 新節（57 勾／2 未勾、收據 53 同 0 變）經獨立重算屬實，兩個未勾格理由仍成立。六項既有發現皆為 Minor 且仍適用，已在 code-summary 揭露為已知限制，不阻擋；無 Critical 或 Major，判定 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | .github/workflows/deploy.yml:568-619（步驟 6a）；.github/workflows/deploy.yml:649-656（`rollback` 條件） | 6a 刻意擋部署（無 `continue-on-error`）。`rollback` 的條件是 `needs.deploy.result == 'failure'` 且為已合併的 PR，所以 6a 失敗會自動還原 last-good、開 revert PR、dispatch Deploy Doctor。6a 要偵測的主要失敗成因（`DEPLOY.md` §5.13 表：Cloudflare 剝除 `Sec-WebSocket-Protocol`、tunnel／DNS 暫時性問題）都不是這個 commit 的程式碼缺陷。後果有三：(a) revert 修不了 Cloudflare 設定，同一個 PR 重新合併還是會失敗；(b) 這次合併會連同 U13 一起被 revert（二者同批進 `ut`）；(c) 6a 的重試窗只有 12 輪 × 約 10 秒，一次暫時性 tunnel 抖動就會觸發自動 revert。`DEPLOY.md` 已誠實寫出「Cloudflare 剝除沒有不改契約的修法」，但沒有說明為什麼用自動 revert 處理一個環境性失敗。程式碼層面（`--max-time`、`\|\| RC=$?`、無 secret、只印狀態列）我找不到缺陷；`test_brain_ws_deploy_probe` 只做文字結構斷言，通過分支只對本機替身驗證過（code-summary §六 D1）。 | 由人決定並記錄：(1) 接受「6a 失敗＝自動 revert」，並在 `DEPLOY.md` §5.13 補一句理由；或 (2) 讓 6a 失敗仍使部署失敗，但把它與程式性失敗區分，使 `rollback` 不自動開 revert PR（例如 6a 失敗只標紅並通知）。同時建議把 `ATTEMPTS` 或間隔拉長，降低暫時性失敗觸發 revert 的機率。 | Resolved (reviewer) |
| R-02 | Major | frontend/tests/e2e/regression.spec.ts；frontend/tests/e2e/estimate-workspace.spec.ts；frontend/tests/e2e/entry-page-live.spec.ts；code-summary.md §六 X1／X2／D1、§十 | `ui-regression` 是真閘門（team.md：`stats.unexpected` 非 0 即 exit 1）。下列內容全部**未在真實 stack 上執行**（本機無 Docker）：`entry-page-live` 5 案、既有 15 案的落點改寫（`regression.spec.ts` 13 案＋`estimate-workspace` 2 案）、突變 X1／X2、6a 對 compose stack 的正反案。`git diff` 顯示改寫把 9 處 `toHaveURL(//workspace/)`（含 `gotoAdmin` helper，8 案共用）弱化為 `not.toHaveURL(//login$/)`（`estimate-workspace` 的 helper 與 `:35` 由 `/(workspace\|cost)/` 同樣弱化）。`not login` 在 `/waiting-approval`、`/403`、任何錯誤頁也成立，保護力改由「其後的既有正向錨點」承擔：「錯誤密碼」案反而強化為 `toHaveURL(//login$/)`；「登出」案新增「登出系統」可見；「Developer」案新增 `sidebar-entry-link` 可見。錨點選擇我認為合理，但**沒有跑過就不知道**這 15 案會不會在 CI 綠。另外，新增 54 案對 15 分鐘 `ui-regression` 時間預算的影響也未量測（本機攔截層 49 案約 37 秒）。 | 在合併前，於 `docker-compose.test.yml` stack 上實際跑完 `regression.spec.ts`、`estimate-workspace.spec.ts`、`entry-page-live.spec.ts`，並補跑 X1／X2。把結果與執行時間寫進 `build-and-test`。未跑完不得宣稱這 20 案為綠。 | Resolved (reviewer) |
| R-03 | Minor | frontend/src/App.tsx（`DefaultRedirect`）；code-summary.md §六 F1 | F1（把 `K1` 判斷移到 `isPending` 之前）執行後 E1 仍綠，所以 E1 對「pending 帳號不得落進入口頁」(AC1.4.3) 的**順序**不具鑑別力。我驗證了原因：`AuthContext.can()` 第一行在 `isPending` 時一律回 false，`RouteGuard.tsx:27` 也先把 pending 導向 `/waiting-approval`，行為上由兩道獨立防線承擔，順序調換在畫面上不可觀察。code-summary 已如實揭露，結論（縱深防禦、非唯一防線）成立，但 AC1.4.3 在 e2e 層沒有一個能因順序錯誤而紅的案例。 | 在 `automation-test-plan.md` 把 F1 記為「無法由 e2e 區分」，不要把 E1 列為保護順序；或接受縱深防禦的現況並寫明。不需改程式。 | Resolved (reviewer) |
| R-04 | Minor | backend/services/work_orchestrator.py:~885；backend/services/hierarchy_facade.py:480-497；backend/tests/test_project_visibility_static.py:37-43 | 大腦還有第五條讀取路徑：`HierarchyFacade.list_diagrams_of_system(principal, system_id=...)`（被 `WorkOrchestrator._list_system_diagrams` 呼叫）。它沒有 `project_visible`，也不在靜態鎖的 `GUARDED_METHODS` 內。它只回請求者**自己擁有**的圖的 `(id, title)`，所以不洩漏別人的名稱，與 ADR-0022 D-2「只有圖不判可見性」的原則一致。但這是一個「系統屬已不可見的專案」仍可被大腦使用的入口：session 中已儲存的 `system_id` 不會在讀取時重新驗證，只在設定時（D-4）與名稱推送時過濾。 | 在 ADR-0022 或 code-summary 明寫這條路徑為已知且接受（只回自有圖）；並確認 session 內已存的 `project_id`／`system_id` 在被移出專案之後，下游能力（需求欄位、成本）自己有授權檢查而非信任儲存的 id。 | Resolved (reviewer) |
| R-05 | Minor | backend/services/brain_gateway.py:878-885、1019；frontend/src/brain/useBrainConnection.ts:103-107 | 握手新增的 `_names_for` 是 `await asyncio.to_thread(_run)`，沒有逾時（本檔 module docstring 規定 `wait_for` 只許出現在 `GatewayTiming`）。`conn` 已 `registry.register`，此時 DB 變慢或卡死會使 `ready` 不送出、握手無限期掛住。前端 `status='awaiting-ready'` 也沒有 ready 逾時（`useBrainConnection.ts` 中未見任何計時器），使用者看到持續連線中、不退避也不放棄。此外，`_names_for` 不在握手 `try` 之內；G1 突變實測顯示若它往外拋，例外會穿出 `_handshake_and_serve` 而非 1011（目前 `_names_for` 自己吞掉所有 `Exception`，所以不可達，但依賴這個不變量）。 | 以 `GatewayTiming.wait_for` 包住 `_names_for`，逾時視同名稱全 null；或明寫為接受風險。前端可考慮 `awaiting-ready` 的逾時。 | Unresolved |
| R-06 | Minor | backend/tests/test_brain_gateway_limits.py:79-81；code-summary.md §六 G6、§十二 第 7 點 | `test_per_user_message_limit_spans_tabs_and_survives_reconnect` 以 `while self.h.registry.total_slots and time.time() < deadline` 等連線釋放，逾時後**不斷言**槽位已清空，直接連第 3 條連線。code-summary 揭露此測試在 G6 還原後首輪紅過一次、之後 31 次皆綠，原因未定位，且本單元在握手中多了一次 `to_thread`，所以不能排除與本單元有關。這是會偶發阻擋 CI 的候選。此測試本身不在本單元 diff 內。 | 補一個 `assertEqual(total_slots, 0)`（或延長等待並失敗時給出明確訊息），使偶發紅燈指向根因；在 `build-and-test` 多跑幾輪確認。 | Unresolved |
| R-07 | Minor | code-summary.md §六 E43／E30；frontend/tests/e2e/entry-page.spec.ts | 三項自述的測試偏差，我評估為可接受但應留在紀錄：(a) E43 把「/me 回 500」改為「/me 回應缺 id」，後者在正式環境不會出現（真實 `/me` 一定帶 id）。真正保護「換人登入清空對話」的是 `subscribeAuthBoundary`，由 E44 與突變 F6 承擔。(b) E30 把「先拒握手再接受」改為「握手完成但快照時機由測試控制」，等價但不是同一個時序。(c) 門面層突變 W1／H1／H3 到不了閘道測試（閘道用 `FakeHierarchy`），以閘道側等價突變 W1′／H1′／H3′ 補做，各自紅 → 綠，這是合理的補救。 | 無程式修改。把 (a) 在 `automation-test-plan.md` 標為「premise 是替代狀態，非正式環境可達」。 | Resolved (reviewer) |
| R-08 | Major | frontend/src/brain/useBrainConnection.ts > `case 'error'` 的 `turnId === null` 分支；backend/services/brain_gateway.py > `_reject`（約 :1176）與主迴圈（約 :1090-1117） | 閘道會對「使用者剛送出的 user_message」回 turnId=null 的 error：頻率超限（`RateLimited`，rate 以 session_key 計，同帳號多分頁共用）、位元組超限、重驗例外都走 `_reject`／`_send_single_error`，不開輪次。前端 `sendUserMessage` 已先 `appendUser`（`pendingConnId` 非 null）並 `setAwaitingReply(true)`。新分支依 `[EP-MB2]`=A 既不 `setAwaitingReply(false)` 也不 `clearPending`，所以這類被拒訊息會讓該分頁輸入列永久停用（BrainInput `canSend` 與重試鈕都看 `awaitingReply`），使用者原句永遠 `data-pending=true`，只有斷線重連才恢復。舊的 `?? ''` 路徑反而會解除。e2e「等待中收到非輪次錯誤只多一則系統提示」把「送出鈕仍停用」寫成通過條件，等於鎖住這個死結；測試只模擬「另一輪進行中」的情境，沒有「被拒的就是這句話」的情境。 | 先與使用者確認 `[EP-MB2]`=A 是否有意涵蓋「被拒的正是等待中的 user_message」。建議：前端無法分辨時，至少讓等待有逃生門（例如 null 錯誤到達時若本連線沒有任何 streaming 的輪次、也沒有 picking 中的反問，就解除 `awaitingReply` 並 `clearPending`），或由閘道對被拒的 user_message 改帶可歸屬的識別。補一個 e2e：連線上無進行中輪次時收到 null 錯誤，輸入列應恢復可用；並在 code-summary 把「被拒 user_message 會卡住」寫成已知限制，若維持 A。 | Resolved (reviewer) |
| R-09 | Minor | frontend/src/brain/brainTranscript.ts > `case 'systemNotice'`（:318-334）；frontend/src/brain/useBrainConnection.ts > `selectCandidate`（:320-326） | 「重開 picking 反問」只看本段有無 `picking`，不確認這則 null 錯誤是否就是對那次選擇的回應。選擇送出後，若另有不相干的 null 錯誤先到（例如 set_work_target／set_sharing_mode 被拒，同樣是 turnId=null），反問會被改回 `default` 並清掉 `pickedId`；之後原選擇若被伺服器接受，`work_items` 的 `resolvePicking` 只處理 `picking` 狀態，這組反問就一直停在可點的 `default`，再點會觸發 T5 的另一則 null 錯誤。ClarifyItem 無 connId，同一分頁內無法分辨；跨分頁則不受影響（每分頁各有 store，錯誤只送給該連線）。 | 接受為已知限制並寫進 code-summary，或在 `selectCandidate` 記下「待回應的選擇」序號，只讓緊接該送出之後到達的第一則 null 錯誤重開反問。 | Resolved (reviewer) |
| R-10 | Minor | frontend/src/brain/brainTranscript.ts > `case 'anchorWorkItems'`（:354-367） | 最後一項若是 notice，錨點取 `last.id`（落在 notice 上）。當 user→notice 之後才收到該輪的 `work_items`（伺服器先送 work_items 再送 token），工作項會掛在系統提示下，而不是等待該輪大腦訊息的 `PENDING_ANCHOR`；之後回覆出現時，工作項在回覆之上、與其所屬輪次分離。notice 本身不屬任何輪次，不應當作錨點。 | 計算錨點時略過尾端的 notice：往前找最後一個 user／brain／clarify 項目決定錨點（user→PENDING），或明確記為已知限制。 | Resolved (reviewer) |
| R-11 | Minor | frontend/src/brain/useBrainConnection.ts > `case 'error'`（:171）、`case 'token'`／`case 'cost_card'`（:145、:152） | `const turnId: string \| null = env.turnId ?? payload.turnId` 只判 `=== null`；`parseInbound` 不驗 `turnId` 欄位存在，若 envelope 與 payload 都缺 turnId（`undefined`），會繞過 notice 分支進入輪次路徑，`turnSegment[undefined]` 建出鍵為 `"undefined"` 的輪次。`token`／`cost_card` 仍用 `?? ''`，契約上必為非 null，但違規時會建出 turnId 為空字串的輪次，正是 merge-blockers 第 2 項描述的覆寫模式。 | `error` 改用 `turnId == null`（或 `typeof turnId !== 'string'`）判斷；`token`／`cost_card` 在 turnId 非字串時丟棄並 `console.warn` 類型，而不是建空字串輪次。 | Resolved (reviewer) |
| R-12 | Minor | frontend/src/brain/useBrainConnection.ts > `setAnnouncement(payload.message)`（:182） | LiveRegion 靠 state 變化播報；連續兩則相同文字的 null 錯誤（例如重複被頻率限制）第二則不會重新播報，畫面雖新增一則 notice，螢幕閱讀器無聲。輪次錯誤路徑有同樣行為，但 null 錯誤因可連發而更容易觸發。 | 播報字串附不可見的序號或以 key 重掛載 live region，或接受並記為已知限制。 | Resolved (reviewer) |
| R-13 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/code-generation/unit-test-instructions.md > 「python scripts/dump_ws_contract.py --check」與「python scripts/dump_openapi.py --check」（第 23、28、39 行） | 指令寫 `python`，而重做段自述本 worktree 只有 `python3`；repo 其餘文件與 `team.md` 用 `python3`。照抄會得到 command not found，使契約一致這道檢查在新環境無法執行。 | 改為 `python3 scripts/...`，與同檔其他指令一致。 | Unresolved |
| R-14 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/code-generation/code-summary.md > §十六之二至之四（E1 語意、`useBrainConnection.ts:169-198` 行號、不 `setAwaitingReply(false)`） | 該節仍以 `[EP-MB2]`=A 舊語意描述（null 錯誤不解除等待、E1 以送出鈕仍停用為通過條件），與現行程式（`[EP-R2]`=A，會解除等待）相反。重做段只用一句已被取代帶過；未讀到重做段的人會讀到兩份相反的行為描述，且該節列的行號已不對。 | 在 §十六之二與之三的標題下就地加一行「已被 `[EP-R2]` 取代，現行行為見 merge-blockers 第 2 列與重做段」，不必改寫原文。 | Unresolved |
| R-15 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/code-generation/code-summary.md > 第 26 項處置 > 一、Step 19「未驗證」段；.github/workflows/deploy.yml:43 | 「失敗的 deploy job 其 outputs 仍可被 rollback 與 notify 讀到」只有 runner 原始碼推論與 notify 的既有前例，沒有任何真實失敗 run 觀察到（歷史上只有一筆早於 notify job 的失敗）；官方 Contexts 文件的範例甚至把失敗 job 的 outputs 畫成空物件。若實際讀不到，行為退回為 6a 失敗也開 revert PR，即裁決失效但不會更糟（失敗方向安全）。X1／X2 突變與 6a 正反案（D1）也只對本機替身驗證過，未在真實 compose stack 上跑。 | 在合併後第一次出現 6a 失敗（或以 workflow_dispatch 加人為讓 6a 失敗的演練，需使用者同意）時，檢查該 run 的 rollback 與 notify 日誌：revert 步驟應為 Skipped，notify 的 BRAIN_WS_PROBE_FAILED 應為 true；結果記入 build-and-test。未觀察前，在 DEPLOY.md 5.13 加一句「此行為尚未在真實失敗 run 上觀察」。 | New |
| R-16 | Minor | DEPLOY.md:2229 與 2239（5.13） | 6a 失敗一律不開 revert PR，包含由本 commit 的程式缺陷造成的失敗（例如大腦 WS 路由被改壞但健康檢查仍通過）。此時站台留在 last-good，但壞 commit 留在 ut，之後每一次合併都會重新部署並再次在 6a 失敗，直到有人處理。文件寫了「由維運者定位後交使用者裁決」，但沒有說明在裁決之前的後續合併會連續失敗，也沒有給維運者判斷「環境性或程式性」的最短判準。 | 在 5.13 補兩句：未裁決前後續合併預期會重複在 6a 失敗；判讀表第 2 欄之外，如何區分程式缺陷（例如對本機 compose stack 跑同一探測，通過則為環境性）。 | New |

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-13 Not re-checked this round

> R-14 Not re-checked this round

> R-15 Not re-checked this round

> R-16 Not re-checked this round
