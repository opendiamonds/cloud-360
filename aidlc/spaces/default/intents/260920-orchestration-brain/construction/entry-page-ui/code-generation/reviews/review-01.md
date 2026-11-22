## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

這是 advisory 單次審查，發現依嚴重度排序，供人在關卡權衡；沒有 Critical，兩項 Major（未超過 2 項的門檻），故 verdict 為 READY。

後端的可見性守門（ADR-0022）以程式閱讀驗證為正確：
- `describe_work_target`、`list_projects`、`list_systems`、`resolve_work_target` 四個讀取方法都把 `project_visible` 設為必填、keyword-only。
- `main.py` 是唯一的組裝點，漏傳會讓啟動以 `TypeError` 失敗。
- 靜態鎖 `S2`／`S3`／`S3b` 涵蓋四個讀取方法，且例外恰一筆。
- 我在 `hierarchy_facade.py`、`hierarchy_service.py`、`brain_gateway.py` 找不到會讓大腦推送使用者看不到的專案、系統名稱的路徑。「不存在」「不屬請求者」「不可見」三者對外逐位元相同。
- `demo` 網關 `backend/services/brain_router.py` 已不存在，`Sidebar.tsx` 的「大腦（示範）」項也已移除。

前端的資料抓取與 reducer 皆符合 team.md 的形狀規則：純 reducer、回傳新物件、`cancelled` flag、無 `eslint-disable`。

主要疑慮不在程式正確性，而在兩處：
1. 本單元最有風險的部署與 e2e 變更（步驟 6a 的自動回滾、既有 15 案改寫）沒有在真實 stack 上跑過。
2. 步驟 6a 的失敗會自動觸發 revert PR，但失敗成因可能是 Cloudflare 設定而非程式碼。

本審查未重跑任何測試（避免破壞 workspace 指紋）。後端 282 案、lint、tsc、validator 的結果引用 conductor 的回報。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | .github/workflows/deploy.yml:568-619（步驟 6a）；.github/workflows/deploy.yml:649-656（`rollback` 條件） | 6a 刻意擋部署（無 `continue-on-error`）。`rollback` 的條件是 `needs.deploy.result == 'failure'` 且為已合併的 PR，所以 6a 失敗會自動還原 last-good、開 revert PR、dispatch Deploy Doctor。6a 要偵測的主要失敗成因（`DEPLOY.md` §5.13 表：Cloudflare 剝除 `Sec-WebSocket-Protocol`、tunnel／DNS 暫時性問題）都不是這個 commit 的程式碼缺陷。後果有三：(a) revert 修不了 Cloudflare 設定，同一個 PR 重新合併還是會失敗；(b) 這次合併會連同 U13 一起被 revert（二者同批進 `ut`）；(c) 6a 的重試窗只有 12 輪 × 約 10 秒，一次暫時性 tunnel 抖動就會觸發自動 revert。`DEPLOY.md` 已誠實寫出「Cloudflare 剝除沒有不改契約的修法」，但沒有說明為什麼用自動 revert 處理一個環境性失敗。程式碼層面（`--max-time`、`\|\| RC=$?`、無 secret、只印狀態列）我找不到缺陷；`test_brain_ws_deploy_probe` 只做文字結構斷言，通過分支只對本機替身驗證過（code-summary §六 D1）。 | 由人決定並記錄：(1) 接受「6a 失敗＝自動 revert」，並在 `DEPLOY.md` §5.13 補一句理由；或 (2) 讓 6a 失敗仍使部署失敗，但把它與程式性失敗區分，使 `rollback` 不自動開 revert PR（例如 6a 失敗只標紅並通知）。同時建議把 `ATTEMPTS` 或間隔拉長，降低暫時性失敗觸發 revert 的機率。 | New |
| R-02 | Major | frontend/tests/e2e/regression.spec.ts；frontend/tests/e2e/estimate-workspace.spec.ts；frontend/tests/e2e/entry-page-live.spec.ts；code-summary.md §六 X1／X2／D1、§十 | `ui-regression` 是真閘門（team.md：`stats.unexpected` 非 0 即 exit 1）。下列內容全部**未在真實 stack 上執行**（本機無 Docker）：`entry-page-live` 5 案、既有 15 案的落點改寫（`regression.spec.ts` 13 案＋`estimate-workspace` 2 案）、突變 X1／X2、6a 對 compose stack 的正反案。`git diff` 顯示改寫把 9 處 `toHaveURL(/\/workspace/)`（含 `gotoAdmin` helper，8 案共用）弱化為 `not.toHaveURL(/\/login$/)`（`estimate-workspace` 的 helper 與 `:35` 由 `/(workspace\|cost)/` 同樣弱化）。`not login` 在 `/waiting-approval`、`/403`、任何錯誤頁也成立，保護力改由「其後的既有正向錨點」承擔：「錯誤密碼」案反而強化為 `toHaveURL(/\/login$/)`；「登出」案新增「登出系統」可見；「Developer」案新增 `sidebar-entry-link` 可見。錨點選擇我認為合理，但**沒有跑過就不知道**這 15 案會不會在 CI 綠。另外，新增 54 案對 15 分鐘 `ui-regression` 時間預算的影響也未量測（本機攔截層 49 案約 37 秒）。 | 在合併前，於 `docker-compose.test.yml` stack 上實際跑完 `regression.spec.ts`、`estimate-workspace.spec.ts`、`entry-page-live.spec.ts`，並補跑 X1／X2。把結果與執行時間寫進 `build-and-test`。未跑完不得宣稱這 20 案為綠。 | New |
| R-03 | Minor | frontend/src/App.tsx（`DefaultRedirect`）；code-summary.md §六 F1 | F1（把 `K1` 判斷移到 `isPending` 之前）執行後 E1 仍綠，所以 E1 對「pending 帳號不得落進入口頁」(AC1.4.3) 的**順序**不具鑑別力。我驗證了原因：`AuthContext.can()` 第一行在 `isPending` 時一律回 false，`RouteGuard.tsx:27` 也先把 pending 導向 `/waiting-approval`，行為上由兩道獨立防線承擔，順序調換在畫面上不可觀察。code-summary 已如實揭露，結論（縱深防禦、非唯一防線）成立，但 AC1.4.3 在 e2e 層沒有一個能因順序錯誤而紅的案例。 | 在 `automation-test-plan.md` 把 F1 記為「無法由 e2e 區分」，不要把 E1 列為保護順序；或接受縱深防禦的現況並寫明。不需改程式。 | New |
| R-04 | Minor | backend/services/work_orchestrator.py:~885；backend/services/hierarchy_facade.py:480-497；backend/tests/test_project_visibility_static.py:37-43 | 大腦還有第五條讀取路徑：`HierarchyFacade.list_diagrams_of_system(principal, system_id=...)`（被 `WorkOrchestrator._list_system_diagrams` 呼叫）。它沒有 `project_visible`，也不在靜態鎖的 `GUARDED_METHODS` 內。它只回請求者**自己擁有**的圖的 `(id, title)`，所以不洩漏別人的名稱，與 ADR-0022 D-2「只有圖不判可見性」的原則一致。但這是一個「系統屬已不可見的專案」仍可被大腦使用的入口：session 中已儲存的 `system_id` 不會在讀取時重新驗證，只在設定時（D-4）與名稱推送時過濾。 | 在 ADR-0022 或 code-summary 明寫這條路徑為已知且接受（只回自有圖）；並確認 session 內已存的 `project_id`／`system_id` 在被移出專案之後，下游能力（需求欄位、成本）自己有授權檢查而非信任儲存的 id。 | New |
| R-05 | Minor | backend/services/brain_gateway.py:878-885、1019；frontend/src/brain/useBrainConnection.ts:103-107 | 握手新增的 `_names_for` 是 `await asyncio.to_thread(_run)`，沒有逾時（本檔 module docstring 規定 `wait_for` 只許出現在 `GatewayTiming`）。`conn` 已 `registry.register`，此時 DB 變慢或卡死會使 `ready` 不送出、握手無限期掛住。前端 `status='awaiting-ready'` 也沒有 ready 逾時（`useBrainConnection.ts` 中未見任何計時器），使用者看到持續連線中、不退避也不放棄。此外，`_names_for` 不在握手 `try` 之內；G1 突變實測顯示若它往外拋，例外會穿出 `_handshake_and_serve` 而非 1011（目前 `_names_for` 自己吞掉所有 `Exception`，所以不可達，但依賴這個不變量）。 | 以 `GatewayTiming.wait_for` 包住 `_names_for`，逾時視同名稱全 null；或明寫為接受風險。前端可考慮 `awaiting-ready` 的逾時。 | New |
| R-06 | Minor | backend/tests/test_brain_gateway_limits.py:79-81；code-summary.md §六 G6、§十二 第 7 點 | `test_per_user_message_limit_spans_tabs_and_survives_reconnect` 以 `while self.h.registry.total_slots and time.time() < deadline` 等連線釋放，逾時後**不斷言**槽位已清空，直接連第 3 條連線。code-summary 揭露此測試在 G6 還原後首輪紅過一次、之後 31 次皆綠，原因未定位，且本單元在握手中多了一次 `to_thread`，所以不能排除與本單元有關。這是會偶發阻擋 CI 的候選。此測試本身不在本單元 diff 內。 | 補一個 `assertEqual(total_slots, 0)`（或延長等待並失敗時給出明確訊息），使偶發紅燈指向根因；在 `build-and-test` 多跑幾輪確認。 | New |
| R-07 | Minor | code-summary.md §六 E43／E30；frontend/tests/e2e/entry-page.spec.ts | 三項自述的測試偏差，我評估為可接受但應留在紀錄：(a) E43 把「/me 回 500」改為「/me 回應缺 id」，後者在正式環境不會出現（真實 `/me` 一定帶 id）。真正保護「換人登入清空對話」的是 `subscribeAuthBoundary`，由 E44 與突變 F6 承擔。(b) E30 把「先拒握手再接受」改為「握手完成但快照時機由測試控制」，等價但不是同一個時序。(c) 門面層突變 W1／H1／H3 到不了閘道測試（閘道用 `FakeHierarchy`），以閘道側等價突變 W1′／H1′／H3′ 補做，各自紅 → 綠，這是合理的補救。 | 無程式修改。把 (a) 在 `automation-test-plan.md` 標為「premise 是替代狀態，非正式環境可達」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 後端 18 模組 | 引用 conductor：282 OK（1 skip，redis-py 缺） | 我未重跑，以避免破壞指紋 |
| `npm run lint`／`tsc -b` | 引用 conductor：0 errors／2 baseline warnings；通過 | 我在新檔未發現 `eslint-disable`、`@ts-ignore`、`as any` |
| `validate_repo_contract`／`validate_env_contract` | 引用 conductor：通過 | — |
| 授權靜態檢查（讀程式碼） | `project_visible` 必填且 keyword-only；`main.py` 為唯一組裝點；`S3_EXCEPTIONS` 恰一筆 | 與 ADR-0022 D-2 至 D-8 一致，未發現可繞過路徑 |
| 密鑰與 token 掃描 | `deploy.yml` 6a 無 `secrets.`、不印標頭值；前端 token 僅在 `subprotocols()`；e2e 僅有假值 `e2e-u14-token` | 未發現硬編碼或外洩 |
| demo 網關合併守門 | `backend/services/brain_router.py` 不存在；`brain_router` 與「大腦（示範）」在 `main.py`、`frontend/src` 皆無命中 | 守門項已滿足；`git log origin/ut..HEAD` 目前 89 個 commit，合併前檢查（code-summary §十一）仍由合併者執行 |

### ADR-0006 四面向（code-summary §十二）的核對

- **IAM**：成立。四個讀取方法收緊為「擁有者範圍 ∩ 可見性」，且有靜態鎖。第五條路徑見 R-04。
- **Encryption**：成立。無新傳輸、無新持久化；`brainTranscript.ts` 只在記憶體；我 grep 到唯一的 `localStorage` 命中在 `brainTranscript.ts` 的檔頭註解（`EPN-13`，非程式）。
- **Network exposure**：成立。6a 的探測不帶身分，伺服器端為 `bearer_token is None` → `_accept_and_close(4401)`。每輪探測會佔一次全域連線預約但立即釋放。
- **Audit logging**：成立。新增一筆白名單內 WARNING `work_target_names_failed`（只帶 `connId`、例外類別名），`HierarchyForbidden` 不記。
