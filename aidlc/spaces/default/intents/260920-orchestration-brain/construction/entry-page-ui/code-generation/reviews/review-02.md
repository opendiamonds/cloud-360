## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-24T12:47:35Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | .github/workflows/deploy.yml:568-619（步驟 6a）；.github/workflows/deploy.yml:649-656（`rollback` 條件） | 6a 刻意擋部署（無 `continue-on-error`）。`rollback` 的條件是 `needs.deploy.result == 'failure'` 且為已合併的 PR，所以 6a 失敗會自動還原 last-good、開 revert PR、dispatch Deploy Doctor。6a 要偵測的主要失敗成因（`DEPLOY.md` §5.13 表：Cloudflare 剝除 `Sec-WebSocket-Protocol`、tunnel／DNS 暫時性問題）都不是這個 commit 的程式碼缺陷。後果有三：(a) revert 修不了 Cloudflare 設定，同一個 PR 重新合併還是會失敗；(b) 這次合併會連同 U13 一起被 revert（二者同批進 `ut`）；(c) 6a 的重試窗只有 12 輪 × 約 10 秒，一次暫時性 tunnel 抖動就會觸發自動 revert。`DEPLOY.md` 已誠實寫出「Cloudflare 剝除沒有不改契約的修法」，但沒有說明為什麼用自動 revert 處理一個環境性失敗。程式碼層面（`--max-time`、`\|\| RC=$?`、無 secret、只印狀態列）我找不到缺陷；`test_brain_ws_deploy_probe` 只做文字結構斷言，通過分支只對本機替身驗證過（code-summary §六 D1）。 | 由人決定並記錄：(1) 接受「6a 失敗＝自動 revert」，並在 `DEPLOY.md` §5.13 補一句理由；或 (2) 讓 6a 失敗仍使部署失敗，但把它與程式性失敗區分，使 `rollback` 不自動開 revert PR（例如 6a 失敗只標紅並通知）。同時建議把 `ATTEMPTS` 或間隔拉長，降低暫時性失敗觸發 revert 的機率。 | New |
| R-02 | Major | frontend/tests/e2e/regression.spec.ts；frontend/tests/e2e/estimate-workspace.spec.ts；frontend/tests/e2e/entry-page-live.spec.ts；code-summary.md §六 X1／X2／D1、§十 | `ui-regression` 是真閘門（team.md：`stats.unexpected` 非 0 即 exit 1）。下列內容全部**未在真實 stack 上執行**（本機無 Docker）：`entry-page-live` 5 案、既有 15 案的落點改寫（`regression.spec.ts` 13 案＋`estimate-workspace` 2 案）、突變 X1／X2、6a 對 compose stack 的正反案。`git diff` 顯示改寫把 9 處 `toHaveURL(//workspace/)`（含 `gotoAdmin` helper，8 案共用）弱化為 `not.toHaveURL(//login$/)`（`estimate-workspace` 的 helper 與 `:35` 由 `/(workspace\|cost)/` 同樣弱化）。`not login` 在 `/waiting-approval`、`/403`、任何錯誤頁也成立，保護力改由「其後的既有正向錨點」承擔：「錯誤密碼」案反而強化為 `toHaveURL(//login$/)`；「登出」案新增「登出系統」可見；「Developer」案新增 `sidebar-entry-link` 可見。錨點選擇我認為合理，但**沒有跑過就不知道**這 15 案會不會在 CI 綠。另外，新增 54 案對 15 分鐘 `ui-regression` 時間預算的影響也未量測（本機攔截層 49 案約 37 秒）。 | 在合併前，於 `docker-compose.test.yml` stack 上實際跑完 `regression.spec.ts`、`estimate-workspace.spec.ts`、`entry-page-live.spec.ts`，並補跑 X1／X2。把結果與執行時間寫進 `build-and-test`。未跑完不得宣稱這 20 案為綠。 | New |
| R-03 | Minor | frontend/src/App.tsx（`DefaultRedirect`）；code-summary.md §六 F1 | F1（把 `K1` 判斷移到 `isPending` 之前）執行後 E1 仍綠，所以 E1 對「pending 帳號不得落進入口頁」(AC1.4.3) 的**順序**不具鑑別力。我驗證了原因：`AuthContext.can()` 第一行在 `isPending` 時一律回 false，`RouteGuard.tsx:27` 也先把 pending 導向 `/waiting-approval`，行為上由兩道獨立防線承擔，順序調換在畫面上不可觀察。code-summary 已如實揭露，結論（縱深防禦、非唯一防線）成立，但 AC1.4.3 在 e2e 層沒有一個能因順序錯誤而紅的案例。 | 在 `automation-test-plan.md` 把 F1 記為「無法由 e2e 區分」，不要把 E1 列為保護順序；或接受縱深防禦的現況並寫明。不需改程式。 | New |
| R-04 | Minor | backend/services/work_orchestrator.py:~885；backend/services/hierarchy_facade.py:480-497；backend/tests/test_project_visibility_static.py:37-43 | 大腦還有第五條讀取路徑：`HierarchyFacade.list_diagrams_of_system(principal, system_id=...)`（被 `WorkOrchestrator._list_system_diagrams` 呼叫）。它沒有 `project_visible`，也不在靜態鎖的 `GUARDED_METHODS` 內。它只回請求者**自己擁有**的圖的 `(id, title)`，所以不洩漏別人的名稱，與 ADR-0022 D-2「只有圖不判可見性」的原則一致。但這是一個「系統屬已不可見的專案」仍可被大腦使用的入口：session 中已儲存的 `system_id` 不會在讀取時重新驗證，只在設定時（D-4）與名稱推送時過濾。 | 在 ADR-0022 或 code-summary 明寫這條路徑為已知且接受（只回自有圖）；並確認 session 內已存的 `project_id`／`system_id` 在被移出專案之後，下游能力（需求欄位、成本）自己有授權檢查而非信任儲存的 id。 | New |
| R-05 | Minor | backend/services/brain_gateway.py:878-885、1019；frontend/src/brain/useBrainConnection.ts:103-107 | 握手新增的 `_names_for` 是 `await asyncio.to_thread(_run)`，沒有逾時（本檔 module docstring 規定 `wait_for` 只許出現在 `GatewayTiming`）。`conn` 已 `registry.register`，此時 DB 變慢或卡死會使 `ready` 不送出、握手無限期掛住。前端 `status='awaiting-ready'` 也沒有 ready 逾時（`useBrainConnection.ts` 中未見任何計時器），使用者看到持續連線中、不退避也不放棄。此外，`_names_for` 不在握手 `try` 之內；G1 突變實測顯示若它往外拋，例外會穿出 `_handshake_and_serve` 而非 1011（目前 `_names_for` 自己吞掉所有 `Exception`，所以不可達，但依賴這個不變量）。 | 以 `GatewayTiming.wait_for` 包住 `_names_for`，逾時視同名稱全 null；或明寫為接受風險。前端可考慮 `awaiting-ready` 的逾時。 | New |
| R-06 | Minor | backend/tests/test_brain_gateway_limits.py:79-81；code-summary.md §六 G6、§十二 第 7 點 | `test_per_user_message_limit_spans_tabs_and_survives_reconnect` 以 `while self.h.registry.total_slots and time.time() < deadline` 等連線釋放，逾時後**不斷言**槽位已清空，直接連第 3 條連線。code-summary 揭露此測試在 G6 還原後首輪紅過一次、之後 31 次皆綠，原因未定位，且本單元在握手中多了一次 `to_thread`，所以不能排除與本單元有關。這是會偶發阻擋 CI 的候選。此測試本身不在本單元 diff 內。 | 補一個 `assertEqual(total_slots, 0)`（或延長等待並失敗時給出明確訊息），使偶發紅燈指向根因；在 `build-and-test` 多跑幾輪確認。 | New |
| R-07 | Minor | code-summary.md §六 E43／E30；frontend/tests/e2e/entry-page.spec.ts | 三項自述的測試偏差，我評估為可接受但應留在紀錄：(a) E43 把「/me 回 500」改為「/me 回應缺 id」，後者在正式環境不會出現（真實 `/me` 一定帶 id）。真正保護「換人登入清空對話」的是 `subscribeAuthBoundary`，由 E44 與突變 F6 承擔。(b) E30 把「先拒握手再接受」改為「握手完成但快照時機由測試控制」，等價但不是同一個時序。(c) 門面層突變 W1／H1／H3 到不了閘道測試（閘道用 `FakeHierarchy`），以閘道側等價突變 W1′／H1′／H3′ 補做，各自紅 → 綠，這是合理的補救。 | 無程式修改。把 (a) 在 `automation-test-plan.md` 標為「premise 是替代狀態，非正式環境可達」。 | New |
| R-08 | Major | frontend/src/brain/useBrainConnection.ts > `case 'error'` 的 `turnId === null` 分支；backend/services/brain_gateway.py > `_reject`（約 :1176）與主迴圈（約 :1090-1117） | 閘道會對「使用者剛送出的 user_message」回 turnId=null 的 error：頻率超限（`RateLimited`，rate 以 session_key 計，同帳號多分頁共用）、位元組超限、重驗例外都走 `_reject`／`_send_single_error`，不開輪次。前端 `sendUserMessage` 已先 `appendUser`（`pendingConnId` 非 null）並 `setAwaitingReply(true)`。新分支依 `[EP-MB2]`=A 既不 `setAwaitingReply(false)` 也不 `clearPending`，所以這類被拒訊息會讓該分頁輸入列永久停用（BrainInput `canSend` 與重試鈕都看 `awaitingReply`），使用者原句永遠 `data-pending=true`，只有斷線重連才恢復。舊的 `?? ''` 路徑反而會解除。e2e「等待中收到非輪次錯誤只多一則系統提示」把「送出鈕仍停用」寫成通過條件，等於鎖住這個死結；測試只模擬「另一輪進行中」的情境，沒有「被拒的就是這句話」的情境。 | 先與使用者確認 `[EP-MB2]`=A 是否有意涵蓋「被拒的正是等待中的 user_message」。建議：前端無法分辨時，至少讓等待有逃生門（例如 null 錯誤到達時若本連線沒有任何 streaming 的輪次、也沒有 picking 中的反問，就解除 `awaitingReply` 並 `clearPending`），或由閘道對被拒的 user_message 改帶可歸屬的識別。補一個 e2e：連線上無進行中輪次時收到 null 錯誤，輸入列應恢復可用；並在 code-summary 把「被拒 user_message 會卡住」寫成已知限制，若維持 A。 | New |
| R-09 | Minor | frontend/src/brain/brainTranscript.ts > `case 'systemNotice'`（:318-334）；frontend/src/brain/useBrainConnection.ts > `selectCandidate`（:320-326） | 「重開 picking 反問」只看本段有無 `picking`，不確認這則 null 錯誤是否就是對那次選擇的回應。選擇送出後，若另有不相干的 null 錯誤先到（例如 set_work_target／set_sharing_mode 被拒，同樣是 turnId=null），反問會被改回 `default` 並清掉 `pickedId`；之後原選擇若被伺服器接受，`work_items` 的 `resolvePicking` 只處理 `picking` 狀態，這組反問就一直停在可點的 `default`，再點會觸發 T5 的另一則 null 錯誤。ClarifyItem 無 connId，同一分頁內無法分辨；跨分頁則不受影響（每分頁各有 store，錯誤只送給該連線）。 | 接受為已知限制並寫進 code-summary，或在 `selectCandidate` 記下「待回應的選擇」序號，只讓緊接該送出之後到達的第一則 null 錯誤重開反問。 | New |
| R-10 | Minor | frontend/src/brain/brainTranscript.ts > `case 'anchorWorkItems'`（:354-367） | 最後一項若是 notice，錨點取 `last.id`（落在 notice 上）。當 user→notice 之後才收到該輪的 `work_items`（伺服器先送 work_items 再送 token），工作項會掛在系統提示下，而不是等待該輪大腦訊息的 `PENDING_ANCHOR`；之後回覆出現時，工作項在回覆之上、與其所屬輪次分離。notice 本身不屬任何輪次，不應當作錨點。 | 計算錨點時略過尾端的 notice：往前找最後一個 user／brain／clarify 項目決定錨點（user→PENDING），或明確記為已知限制。 | New |
| R-11 | Minor | frontend/src/brain/useBrainConnection.ts > `case 'error'`（:171）、`case 'token'`／`case 'cost_card'`（:145、:152） | `const turnId: string \| null = env.turnId ?? payload.turnId` 只判 `=== null`；`parseInbound` 不驗 `turnId` 欄位存在，若 envelope 與 payload 都缺 turnId（`undefined`），會繞過 notice 分支進入輪次路徑，`turnSegment[undefined]` 建出鍵為 `"undefined"` 的輪次。`token`／`cost_card` 仍用 `?? ''`，契約上必為非 null，但違規時會建出 turnId 為空字串的輪次，正是 merge-blockers 第 2 項描述的覆寫模式。 | `error` 改用 `turnId == null`（或 `typeof turnId !== 'string'`）判斷；`token`／`cost_card` 在 turnId 非字串時丟棄並 `console.warn` 類型，而不是建空字串輪次。 | New |
| R-12 | Minor | frontend/src/brain/useBrainConnection.ts > `setAnnouncement(payload.message)`（:182） | LiveRegion 靠 state 變化播報；連續兩則相同文字的 null 錯誤（例如重複被頻率限制）第二則不會重新播報，畫面雖新增一則 notice，螢幕閱讀器無聲。輪次錯誤路徑有同樣行為，但 null 錯誤因可連發而更容易觸發。 | 播報字串附不可見的序號或以 key 重掛載 live region，或接受並記為已知限制。 | New |

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
| 唯讀閱讀（`useBrainConnection.ts`、`brainTranscript.ts`、`ConversationView.tsx`、`wsFrames.ts`、e2e 四案本文、`brain_gateway.py` 錯誤路徑） | 完成 | 依指示未執行 build、Playwright、tsc；`data-pending` 為純 data 屬性，無 a11y 或 lint 影響；四個 e2e 案的斷言與所稱突變（M-N1 還原 `?? ''`、M-N2 解除等待、M-N3 改 resolved）確實會使對應案例失敗，但沒有任何案例涵蓋「被拒的就是等待中那一句」。閘道（T1–T9，null 僅用於非輪次錯誤）與前端對輪次內錯誤的分流一致。 |

### Summary

null 錯誤不再污染輪次、notice 與反問重開的主路徑正確；主要缺口是閘道會對被拒的 user_message 回 turnId=null，而新分支依裁決不解除等待，導致該分頁輸入列卡死，需請使用者確認 `[EP-MB2]`=A 是否有意如此。其餘為錨點、重開判準與防禦性型別檢查的小問題。
