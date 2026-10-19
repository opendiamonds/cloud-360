# Code Summary — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T13:53:43Z（`date -u` 取值）。工作分支 `danniel/docs/orchestration-brain-ideation`；本站未 commit、未 push。
> 方法論 `test-after`（`code-generation-plan.md` §Testing Contract，`standard`）：每一層先實作、再寫並執行該層測試。
> 計畫檔只勾核取方塊；`unit-test-instructions.md` 未改動。

## 一、步驟完成狀態

| Step | 狀態 | 備註 |
|---|---|---|
| 1 結構骨架、ADR 落檔、事實複驗 | 完成 | ADR 落檔；三個前端目錄以第一個檔帶出；全部事實與計畫一致（§二） |
| 2 測試執行器就緒 | 完成 | 基準見 §三 |
| 3–4 Data model | 完成 | 突變 C1、C2 紅 → 綠 |
| 5–6 Repository | 完成 | 突變 V1、V2 紅 → 綠 |
| 7–8 Business logic | 完成 | 突變 W1–W6、H1–H4 紅 → 綠（Step 8 的 `S3` 在 Step 9 完成前暫紅，Step 9 後綠，見 §十二） |
| 9–10 API／endpoint | 完成 | 突變 G1–G8 紅 → 綠（G1 紅的形狀與計畫字面不同，見 §六） |
| 11 Frontend 實作 | 完成 | lint 0 errors／2 warnings（= 基準）；build、check:ws-types、check:types 綠 |
| 12 Frontend 測試 | **部分** | 攔截層 49 案全綠；真實 stack 層 5 案與既有 15 案已改寫但**未執行**（本機 Docker daemon 未啟動）；F 系列 26 道、C3、T1–T4 已執行；X1、X2 未執行 |
| 13 Environment／build | **部分** | 6a 與其測試完成、D2–D4 紅 → 綠；**第 3 個核取方塊（對 compose stack 的本機驗證）未勾**——只對本機最小替身伺服器驗證了腳本分支（§六 D1） |
| 14 Documentation | 完成 | `DEPLOY.md` 新增 §5.13 |
| 15 Traceability 與 code-summary | 完成（本檔） | 合併前檢查交接給合併者（§十一） |

## 二、Step 1 複驗紀錄（唯讀，逐項附行號；全部與計畫一致，未停下）

| 檔：行 | 計畫的事實 | 實測 |
|---|---|---|
| `backend/services/brain_gateway.py:565` | `_HierarchyResolver.__init__` | 一致（`:564` class、`:565` init） |
| `:593-622` | `BrainGateway.__init__` | 一致 |
| `:820-858` | 握手：第一個 try（`load`＋`list_items`）、第二個 try（ready＋快照） | 一致（`:822-834`、`:840-853`） |
| `:869-907` | `_snapshot_envelopes`、`_work_target_envelope` | 一致 |
| `:1226-1243` | `_build_catalog` 三個呼叫點 `:1230`／`:1235`／`:1239` | 一致 |
| `:1301-1324` | `_set_target_confirmed`，扇出 `:1323` | 一致 |
| `:1403-1451` | `_on_set_work_target`（扇出 `:1426`）、`_on_set_sharing_mode`（`fanout_many` `:1445-1451`） | 一致 |
| `:1569-1598` | `build_brain_gateway(app)` | 一致 |
| `hierarchy_facade.py:366-405` | `list_projects`／`list_systems`／`resolve_work_target` | 一致；`:238-254` 的寫入路徑註解段一致 |
| `membership_facade.py:518-533` | `project_visibility` 閉包 | 一致 |
| `membership_service.py:337-379` | `_visible_project_ids_select`、`visible_project_ids`、`is_project_visible` | 一致 |
| `brain_ws_contract.py:282-302` | `WorkTargetPayload` | 一致 |
| `main.py:82-85` | startup 註解與 `build_brain_gateway(app)` | 一致（`:84`） |
| `tests/test_hierarchy_service.py:191`／`:199`／`:212-216` | 五處呼叫 | 一致 |
| `tests/test_brain_gateway_startup.py:60` | `side_effect=lambda app: …` | 一致 |
| `tests/brain_gateway_fakes.py:322`、`:343-355` | `_HierarchyResolver(...)`、`BrainGateway(...)` | 一致 |
| `WorkspacePage.tsx:116-129`、`:152-164`、`:269-301`、`:304`、`:327`、`:340`、`:441` | handleCanvasExit、fetchDiagrams、bootstrap effect、handleLoadDiagram、handleNewDiagram、handleDeleteDiagram、帶參數進評核 | 一致（`:282` bootstrap 開圖、`:313` 下拉開圖亦一致） |
| `AssessmentPage.tsx:139-158`、`:187`、`:232-248`、`:560`、`:743`、`:813`、`:1268` | state、fetchDiagrams、選定圖與清單 effect、四個改變選定圖的位置 | 一致 |
| `App.tsx:24-34`、`:234-241` | DefaultRedirect、`*` 路由 | 一致 |
| `AuthContext.tsx:56`、`:82-93`；`LoginPage.tsx:107` | logout、login；登入後 `navigate('/')` | 一致 |
| `eslint.config.js:42-66` | 三條子協定規則 | 一致 |
| `Sidebar.tsx:214-215` | `U23` 註解「U14 的『入口』尚未落地」 | 一致 |
| `deploy.yml:447`、`:570`、`:596-602` | Redis 重啟驗證、last-good、rollback 條件 | 一致 |
| `test_mcp_bridge_deploy.py:101-104` | mcp 健康步驟的前後步驟釘子 | 一致 |

**呼叫點 grep**（`grep -rn --include='*.py' "\.list_projects(\|\.list_systems(\|\.resolve_work_target(\|\.describe_work_target(" backend`，非測試命中）：`brain_gateway.py:572`、`:1230`、`:1235`、`:1239`；`session_store.py:387`；`hierarchy_facade.py` 對 service 層的 `:369`、`:379`、`:399`、`:486`（`list_systems_unscoped` 的 service 呼叫）——與計畫一致。

## 三、Step 2 基準（改動前）

| 指令（`backend/` 或 `frontend/`） | 結果 |
|---|---|
| 計畫 §二「基準」16 個模組 | `Ran 235 tests … OK (skipped=1)`；skip 為既有 `test_unreachable_redis_does_not_block_startup_but_handshake_closes_1011`（本機未裝 redis-py） |
| `python3 scripts/dump_ws_contract.py --check`／`dump_openapi.py --check` | 皆一致 |
| `npm run lint` | `0 errors, 2 warnings`（`AssessmentPage.tsx:365`、`WorkspacePage.tsx:302`，皆 exhaustive-deps；`team.md` 記載的 3 則已過時） |
| `npm run build`／`check:ws-types`／`check:types` | 綠 |
| `npx playwright test …entry-page*.spec.ts --list` | `No tests found` ／ `Total: 0 tests`（檔案尚不存在，非設定錯誤） |

工作樹註：本 worktree 沒有裸 `python`，計畫中的 `python scripts/...` 一律以 `python3` 執行。

## 四、Step 15 全單元重跑（改動後）

| 指令 | 結果 |
|---|---|
| 計畫 §二「全單元」18 個模組 | `Ran 282 tests … OK (skipped=1)`（同一既有 skip） |
| 本單元新增後端案 | 47 案（`test_ws_contract` 2、`test_describe_work_target` 22、`test_hierarchy_service` 6、`test_project_visibility_static` 1（`S3b`）、`test_brain_gateway_startup` 1、`test_brain_gateway_handshake` 3、`test_brain_gateway_turn` 8、`test_brain_ws_deploy_probe` 4）；`S2`／`S3` 為改寫既有兩案 |
| `dump_ws_contract.py --check`、`dump_openapi.py --check` | 皆一致（`openapi.json`、`api.d.ts` 零變更） |
| `npm run check:ws-types`、`npm run lint`、`npm run build` | 綠；lint `0 errors, 2 warnings`（未高於基準） |
| `npx playwright test tests/e2e/entry-page.spec.ts`（攔截層，對本機同源的 `vite preview`） | **49 passed**（最後一次 36.6s；Step 12 期間另有多次全綠） |
| `entry-page-live.spec.ts`（5）、`regression.spec.ts`（13）、`estimate-workspace.spec.ts`（2） | **未執行**：需 `docker-compose.test.yml` stack，本機 Docker daemon 未啟動；`--list` 可列出（54＋16） |
| `python3 scripts/validate_repo_contract.py`、`validate_env_contract.py` | 皆通過 |

**攔截層的服務方式（如實記載）**：以 `VITE_API_BASE_URL=http://localhost:4173 npx vite build --outDir <scratchpad>/dist-e2e` 建一份同源 bundle、`vite preview --port 4173` 服務，`BASE_URL=http://localhost:4173` 執行——API 與 WS 皆落在同一個 origin、由 spec 攔截（避免跨來源 CORS）。CI 的 `ui-regression` 以 compose stack 的 nginx 服務（同源），行為相同。

## 五、帶入的 26 項的落點（`../carried-review-items.md`）

| ID | 站別 | 落點 |
|---|---|---|
| R-01 | functional-design（Major） | `hierarchy_facade.describe_work_target`（必填 `project_visible`、ADR D-2）＋ `hierarchy_service.describe_work_target`；`brain_gateway._names_for` 以注入的 `membership_facade_factory` 取閉包；測試 (a)／(b)／(b2)／(c)（`test_describe_work_target.py`）、(b')（`test_brain_gateway_turn.py`） |
| R-02 | functional-design（Major） | `useWorkspaceTargetSync.decideInitialAlignment` 的 `hold`；SyncNotice「開啟這張圖」＋ `window.confirm`；E30（含乾淨畫布對照組）；突變 F8 |
| R-03 | functional-design（Major） | `subscribeAuthBoundary`（`auth-context.ts`／`AuthContext.tsx`，login／logout 第一行通知）＋ `BrainTranscriptProvider` 訂閱；`App.tsx` 無 key；E43、E44；`grep -c "key="` 為 0；突變 F5、F6、T4 |
| R-04 | functional-design | `src/brain/testing/wsFrames.ts`（只收原始型別、先宣告具名 payload 型別）；`eslint.config.js` tests 區塊；突變 C3、T1 |
| R-05 | functional-design | `pendingEchoes`（≤ 8、ready 清空；刪除時的 null 也納入，見 §九）；E32；突變 F11 |
| R-06 | functional-design | `WorkspacePage.fetchDiagrams` 回傳 `{ ok, list }`、`listOk` 為假時兩向不同步並提示（E36、F23）；`""` 顯示「（未命名）」（E23、F24） |
| R-07 | functional-design | ADR D-9 落檔（`inception/decisions/0022-…`）；合併前三項檢查交接（§十一） |
| R-08 | functional-design | `openedBy`（`markOrigin`）與 `decideInitialAlignment` 的 bootstrap 不回寫；E35；突變 F12 |
| R-01 | nfr-requirements（Major） | `list_projects`／`list_systems` 必填 `project_visible`；`_build_catalog` 三個呼叫點注入；GT2（被移出者說前專案名 → not_found、0 clarify、0 設定）與 GT3（可見同名唯一命中）；`BrainReadVisibilityTest`；突變 H1、H2、G5（另 H1′） |
| R-02 | nfr-requirements（Major） | `StatementCountTest`：完整三元組恰 5、只有圖 2、1 與 50 個專案相同、`_names_for` 快照 ≤ 15 且只開 1 個 session；突變 W5、G3 |
| R-03 | nfr-requirements | `membership_facade_factory` 必填注入、`main.py` 組裝；`S3_EXCEPTIONS` 恰一筆（`S3b`）；突變 G7 |
| R-04 | nfr-requirements | StrictMode 三項 code review（§八）；`vite dev` 手動案交 `tcms-test-cases`（§十） |
| R-05 | nfr-requirements | 4403：不導航、`refreshMe()` 每實例至多一次、子頁面掛點依 `K1`；E9–E11；突變 F7（E10 經補強後紅，見 §六） |
| R-06 | nfr-requirements | `utils/unsavedWork.ts`（`isCanvasDirty` 原樣抽出、`hasUnsavedAssessmentWork`）；E31；突變 F9 |
| R-07 | nfr-requirements | 抖動維持 ×[0.8, 1.0]、理由改述為「降低同秒重連」（`brainProtocol.ts` 註解）；宣告支援同一使用者 3 個分頁完整跑完 60 秒退避（performance-design §一之三的 ⌊30／9⌋） |
| R-01 | nfr-design（Major） | 只有圖不推導上層、不判可見性、保留圖名（facade `describe_work_target` 的 `explicit` 分支）；(e2) facade 與 turn 層皆斷言 `{null, null, "<圖名>"}`；突變 W3 |
| R-02 | nfr-design（Major） | `MembershipFacade.project_visibility` 的實例暫存（ADR D-5）：`list_projects` 固定 3 條、目錄可見性成本 ＋1；`VisibilityBatchTest`、`CatalogStatementCountTest`（N＝1 恰 6、N＝8 恰 27、N＝51 截斷恰 3）；突變 V2；總數仍隨 N 線性如實揭露（§十二） |
| R-03 | nfr-design | (b2) 夾具（另是第二專案成員）；原 M2 改由等價突變 V1 承接，(b2) 與 `VisibilityBatchTest` 第 3 案皆紅；原 M2 仍由 `U23` 的 `test_project_visibility_queries` 承擔 |
| R-04 | nfr-design | `HierarchyForbidden` 不記 log、其他例外記 `work_target_names_failed`；handshake 兩案（`assertLogs` 一筆／`assertNoLogs`）；突變 G2 |
| R-05 | nfr-design | 無連線時同步掛點全部 no-op（`setWorkTarget` 未 ready 不送、回 false）；E38；突變 F22 |
| R-06 | nfr-design | `WorkTargetNames.project_ids` 收集三元組出現的每個相異專案（圖層 left join 取系統所屬專案，不增語句數）；(i)；突變 W4 |
| R-07 | nfr-design | 章節引用更正入回補表（§七）；`brainProtocol.ts` 的 `delayFor(n)` 註解寫明 n 自 0 起算 |
| R-01 | infrastructure-design（Major） | `regression.spec.ts` 錯誤密碼案改 `toHaveURL(/\/login$/)`，`@step`／`@pass`／`@note` 同步；突變 X1 **未執行**（需真實 stack） |
| R-02 | infrastructure-design（Major） | Developer 案在 `toHaveCount(0)` 前加 `sidebar-entry-link` 可見；其餘 12 案的正向錨點見 §十三；突變 X2 **未執行** |
| R-03 | infrastructure-design | 6a 失敗時印出最後一輪狀態列、「協定標頭：有／無」、`curl exit=`；`test_brain_ws_deploy_probe.test_failure_branch_prints_three_diagnostics` 鎖住；本機替身驗證見 §六 D1 |
| R-04 | infrastructure-design | 「管理員登入後進入工作區」改名為「管理員登入後進入入口頁」→ Kiwi 舊案例成孤兒，交 `tcms-test-cases` 人工停用並記入 `tcms-sync-report.md`（§十） |

## 六、突變結果（§五 全表；每道：套用 → 確認紅 → 還原 → 確認綠）

後端（指令為各步的單元指令；frontend 系列每道都重建 bundle 後跑對應案）。

| 代號 | 改了什麼 | 紅的案（實測） | 還原後 |
|---|---|---|---|
| C1 | `brain_ws_contract.py` `projectName` 加 `default=None` | `Adr0022NameFieldTest.test_missing_any_name_field_is_rejected`（missing='projectName'）：`AssertionError: ValidationError not raised`；附帶：JSON schema `required` 不含 `projectName`、`dump_ws_contract.py --check` rc=1 | 綠（2 案 OK、`--check` 一致） |
| C2 | `brain_ws_contract.py` `diagramName` description 改字、不重 dump | `dump_ws_contract.py --check` rc=1「規格檔已漂移」 | 綠（rc=0） |
| V1 | `membership_facade.py` 閉包 `return int(project_id) in ids` → `return bool(ids)` | Step 6：`VisibilityBatchTest` 第 3 案 `test_non_empty_visible_set_without_target_is_false`（`True is not false`），另兩案亦紅；Step 8 的 (b2) 結果見下方 V1（Step 8 重跑）列 | 綠（3 案 OK） |
| V2 | `membership_facade.py` 拿掉暫存、每次 `membership_service.is_project_visible` | `VisibilityBatchTest` 第 1 案 `10 != 1`、第 2 案 `2 != 1`；`StatementCountTest` 的 `list_projects` 等量案見 V2（Step 8 重跑）列 | 綠 |
| V1（Step 8 重跑） | 同 V1 | `DescribeWorkTargetTest.test_b2_…`、`test_i_…` 紅（(b2) 必紅成立） | 綠（12 案 OK） |
| V2（Step 8 重跑） | 同 V2 | `StatementCountTest.test_list_projects_is_three_statements_for_one_and_fifty_projects` 紅 | 綠 |
| W1 | `hierarchy_facade.py` `describe_work_target` 刪除第 ③ 步（可見性判定兩行） | `test_b_…`、`test_b2_…`、`test_i_…`、`StatementCountTest` 兩個完整三元組案（少 1 條 SQL）紅；(b') 見 W1（Step 10 重跑） | 綠（53 案 OK） |
| W2 | `describe_work_target` 的 `project_visible` 改 `Optional[...] = None`，為 None 時略過 ③ | `test_h_missing_project_visible_is_type_error`、`test_S2_project_visible_is_required_keyword_only` 紅 | 綠（20 案 OK） |
| W3 | ③ 的條件拿掉 `found.explicit`（只有圖也判可見性） | `test_e2_diagram_only_under_former_project_keeps_diagram_name` 紅 | 綠 |
| W4 | ③ 改為只判 `project_id` 參數 | `test_i_system_under_another_invisible_project_gives_all_null` 紅 | 綠 |
| W5 | `hierarchy_service.describe_work_target` 系統層改用 `assert_system_owned_by`（try/except 吞查不到） | `StatementCountTest.test_full_triple_is_exactly_five_statements`、`…_one_and_fifty_projects` 紅（語句數斷言） | 綠 |
| W6 | ③ 不可見改 `raise HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)` | `test_b_…`、`test_b2_…`、`test_i_…` 以 ERROR 紅 | 綠 |
| H1 | `list_projects` 拿掉可見性過濾 | `BrainReadVisibilityTest.test_list_projects_excludes_former_project_of_removed_creator` 紅；GT2 見 H1（Step 10 重跑） | 綠（6 案 OK） |
| H2 | `list_systems` 不可見時 `return []` | `test_list_systems_of_former_project_is_not_found_with_project_detail` 紅 | 綠 |
| H3 | `resolve_work_target` 可見性判定改 `if True: return resolved` | `test_EPD1_1_…`、`test_EPD1_2_…` 紅；GT4 見 H3（Step 10 重跑） | 綠 |
| H4 | 由圖推導也拋 `HierarchyNotFound`（`if True: raise …`） | `test_EPD1_2_diagram_only_under_former_project_keeps_only_diagram` 以 ERROR 紅 | 綠 |
| G1 | `_names_for` 內層 `except Exception` 與外層 `except Exception` 各加 `raise`（往外拋） | `WorkTargetNamesSnapshotTest.test_names_failure_still_completes_handshake_and_logs_once` 以 ERROR 紅：`RuntimeError: e2e-u14-SECRET-MARKER` 由 `_handshake_and_serve` 傳出、握手未完成。**與計畫字面差異**：計畫寫「得 1011」，實際是例外直接穿出 handler（名稱查詢位在握手第二個 try 之外），測試以未收到 ready／例外呈現紅燈——紅的方向相同、形狀不同，如實記載 | 綠（3 案 OK） |
| G2 | `except HierarchyForbidden` 也記 `work_target_names_failed` | `test_forbidden_names_are_null_without_any_log` 紅（`assertNoLogs` 收到 WARNING） | 綠 |
| G3 | `_names_for` 迴圈內每組各開一個 session 與 facade | `test_snapshot_work_target_carries_names_with_one_session`（不同 session 數斷言紅）、`StatementCountTest.test_names_for_snapshot_is_at_most_fifteen_with_one_session`（`session_factory` 呼叫次數斷言）紅 | 綠（8 案 OK） |
| G4 | `_on_set_work_target` 扇出改 `_work_target_envelope(session, segment_id, _NO_NAMES)` | `test_GT1_set_work_target_fanout_carries_names` 紅；另 `test_b_prime_…`、`test_e2_…` 亦紅 | 綠 |
| G5 | `_build_catalog` 逐專案 `list_systems` 改傳 `project_visible=lambda _: True` | `test_S3_every_write_call_injects_project_visibility` 紅 | 綠 |
| G6 | `brain_gateway.py` 加 `from services.membership_facade import MembershipFacade` | `test_brain_gateway_limits` 的 `test_forbidden_imports_names_and_hand_built_messages`（imported='services.membership_facade'）紅 | 還原後首輪 `test_per_user_message_limit_spans_tabs_and_survives_reconnect` 偶發紅一次；之後連跑 6 次全模組綠、`RateLimitTest` 單獨 25 次 0 紅——列為偶發，見 code-summary 揭露 |
| G7 | `main.py` 改回 `build_brain_gateway(app)`（漏傳 factory） | `test_gateway_is_built_after_routing_config_and_before_init_db_and_shut_down` 與 `test_missing_redis_settings_or_default_user_fail_startup` 四個子案以 ERROR 紅 | 綠（5 OK＋1 既有 skip） |
| G8 | `_named_work_target_envelope` 對不可見專案改送 `error(UNAUTHORIZED)` | `test_b_prime_invisible_and_nonexistent_serialize_identically` 以 ERROR 紅（情境 A 收到 error 而非 work_target） | 綠 |
| W1（Step 10 重跑） | 同 W1（facade 刪 ③） | 閘道層 8 案**仍綠**：閘道測試以 `FakeHierarchy` 替身取代 facade（`unit-test-instructions.md` §一），facade 突變觸不到；W1 由 Step 8 的 facade 案承擔。**補做閘道側等價突變 W1′**：`_names_for` 改傳 `project_visible=lambda _pid: True` → `test_b_prime_…` 紅、還原綠 | 綠 |
| H1（Step 10 重跑） | 同 H1 | 閘道層仍綠（理由同上）。**閘道側等價 H1′**：`_build_catalog` 的 `list_projects` 改傳 `lambda _pid: True` → `test_GT2_…`、`test_GT3_…` 紅、還原綠 | 綠 |
| H3（Step 10 重跑） | 同 H3 | 閘道層仍綠（理由同上）。**閘道側等價 H3′**：`_HierarchyResolver` 改傳 `lambda _pid: True` → `test_GT4_…`、`test_e2_…` 紅、還原綠 | 綠 |

前端、契約、lint、部署：

| 代號 | 改了什麼 | 紅的案（實測） | 還原後 |
|---|---|---|---|
| F1 | `App.tsx` `DefaultRedirect` 把 `K1` 判斷移到 `isPending` 之前 | **未紅**：E1 仍綠。原因：既有 `AuthContext.can()` 在 `isPending` 時一律回 false（`AuthContext.tsx` 的 `can` 第一行），故順序調換在畫面上不可觀察——`isPending` 在前是縱深防禦而非唯一防線。突變未能證明 E1 的鑑別力，如實記載 | 綠 |
| F2 | `useBrainConnection.sendUserMessage` 加 `sessionStorage.setItem('brain-last-utterance', text)` | E45「對話後瀏覽器儲存不含原句」紅（session 鍵集合多 1） | 綠 |
| F3 | `onmessage` 開頭 `console.warn(JSON.stringify(env.payload))`（計畫字面為 `console.warn(payload)`；改為字串化使主控台文字含名稱，物件形式在 `msg.text()` 只得到預覽） | E46「主控台不含原句名稱與 token」紅（出現 `e2e-u14-機密專案`） | 綠 |
| F4 | 連線網址加 `?token=${accessToken}` | E5 紅：`Received string: "ws://localhost:4173/api/brain/ws?token=e2e-u14-token"`（第一次執行時因攔截 glob 不含查詢字串而以「卡在 connecting」紅；改為正規式攔截後由網址斷言紅） | 綠 |
| F5 | `BrainTranscriptContext.tsx` 拿掉 `subscribeAuthBoundary` 訂閱；`App.tsx` 改以 `user?.id ?? 'anon'` 為 key 掛 Provider | E43「登出再換人登入時對話區清空」紅（B 登入後入口頁仍有 `e2e-u14-A的原句`；/me 缺 id 使兩人同 key） | 綠 |
| F6 | `AuthContext.login()` 拿掉 `notifyAuthBoundary()`（只在 logout 通知） | E44「不登出直接換人登入時對話區清空」紅（B 登入後仍見 A 的原句與回覆） | 綠 |
| F7 | `useBrainConnection` 收到 4403 且非入口頁時 `navigate('/')` | 第一次執行**未紅**：導到 `/` 後 `refreshMe()` 完成、`DefaultRedirect` 又導回 `/workspace`，最終狀態收斂，E10 只驗最終 URL 與畫布故看不到繞行。E10 補「4403 之後 history 變更紀錄為空」與「大腦連線仍 1 條」兩個斷言後重跑：紅（history 紀錄 4 筆）。補強後的 E10 原樣通過 | 綠 |
| F8 | `useWorkspaceTargetSync` 的 `unsaved` 恆為 false | E30 紅：「目前畫布有未儲存的變更，沒有自動開啟」不存在（畫布被自動換成圖 12） | 綠 |
| F9 | `useAssessmentTargetSync` 的 `unsaved` 恆為 false（拿掉 `hasUnsavedAssessmentWork`） | E31 紅：「沒有自動開啟」提示不存在（自動改選圖 12） | 綠 |
| F10 | `isOwnedDiagram` 拿掉 `is_owner === true` 條件 | E33 紅：送出 `set_work_target{diagramId:'21'}`（別人分享的圖被回寫） | 綠 |
| F11 | 回聲判定改為只比對最近一次送出值 | E32 紅：圖 12 的回聲到達時出現「作業對象已改為」 | 綠 |
| F12 | `decideInitialAlignment` 拿掉 `openedBy === 'bootstrap'` 條件 | E35 紅：bootstrap 開的圖 11 被回寫，作業對象的系統層消失（脈絡列無系統名） | 綠 |
| F13 | token 不立即 dispatch，緩衝到 done 時才一次寫入 | E12 紅：送 token 未送 done 時文字 `e2e-u14-第一段e2e-u14-第二段` 不存在 | 綠 |
| F14 | `classifyClose` 拿掉 4401 分支（4401 走退避） | E7 紅：「連線已失效，請重新登入」不存在 | 綠 |
| F15 | 放棄判準改為失敗滿 3 次（不看累計時間） | E8 紅：放棄前的握手次數 4（期望 8–9） | 綠 |
| F16 | `append` 拿掉 500 則上限 | E42 紅：`brain-transcript-truncated` 不存在 | 綠 |
| F17 | 對照改回「段＋索引」：附加時記索引、截斷時不調整、更新時依記下的索引寫入 | E42 紅：被移除那一輪的後續沒有另建一則（`t42-1` 的訊息不存在——token 被寫進記下索引處的別則訊息） | 綠 |
| F18 | 重連後保留本地工作項（ready 不清空、work_items 以合併取代整份取代） | E41 紅：重連後常駐區仍有舊工作項 w1 | 綠 |
| F19 | 入口頁掛載時多一次 `fetch('/api/brain/state')` | E47 紅：請求集合出現 `GET /api/brain/state`，不在既有端點允許清單內 | 綠 |
| F20 | `StreamingMessage` 拿掉 `aria-busy` | E12 紅：串流中 `aria-busy` 不為 "true" | 綠 |
| F21 | 收到 `cost_card` 時 `navigate('/cost')` | E21 紅：頁面離開入口頁，卡片文字不存在 | 綠 |
| F22 | 工作區 `useBrainConnection` 的 `enabled` 恆為 true（無 K1 仍連線、同步掛點仍可送出） | E38 紅：大腦連線 1 條（期望 0） | 綠 |
| F23 | 忽略 `listOk`（決策、回寫與提示三處都不看清單是否成功） | E36 紅：「無法確認這張圖的擁有者，未同步作業對象」不存在（顯示的是未存檔提示） | 綠 |
| F24 | 名稱為 `""` 時顯示「（無法顯示名稱）」 | E23 紅：期望「（未命名）」，實得「（無法顯示名稱）」 | 綠 |
| F25 | 跳過 `ready.protocolVersion` 核對 | E5 紅：「版本不相容，請重新整理頁面」不存在 | 綠 |
| F26 | cleanup 不關閉連線 | E6 紅：切換 5 次後未關閉的大腦連線 6 條（期望 1） | 綠 |
| C3 | `brain_ws_contract.py` 把 `diagramName` 改名為 `diagramTitle`，重 dump、`npm run gen:ws-types` | `npm run build` 紅（rc=2）：`src/brain/testing/wsFrames.ts(131,5): error TS2353 … 'diagramName' does not exist`，另 `brainProtocol.ts`、`ContextBar.tsx` 各一則 TS2339 | 三檔還原並重產；`ws-contract.json`、`ws-contract.d.ts` 與突變前逐位元相同（cmp），`npm run build` rc=0、`dump_ws_contract.py --check` 一致 |
| T1 | `entry-page.spec.ts` 暫加 `{ type: 'work_target', payload: {...} }` | `eslint` 紅：「e2e 不得手寫 WS 訊框…」 | 移除後 lint 綠 |
| T2 | `frontend/tests/e2e/` 暫放 `new WebSocket(u, ['bearer.x'])` | `eslint` 紅：「subprotocol 必須由 ws-contract.d.ts 的 WsSubprotocol 取值…」（tests 區塊確實展開了 `WS_SUBPROTOCOL_RESTRICTIONS`） | 刪除後 `npm run lint` 0 errors |
| T3 | `EntryPage.tsx` 加 `import '../brain/testing/wsFrames'` | Step 11 grep（app 程式匯入 brain/testing）命中 1 | 還原後 0 |
| T4 | `App.tsx` 在 `BrowserRouter` 之上的 Provider 加 `key=` | Step 11 grep `key=` 於 `App.tsx` 為 1 | 還原後 0 |
| X1 | 計畫：以 `page.route` 讓 `/api/auth/login` 對錯誤密碼回 200 ＋ token，跑 `錯誤密碼被拒並停留在登入頁` | **未執行**：該測試需真實 stack（`docker-compose.test.yml`），本機 Docker daemon 未啟動 | — |
| X2 | 計畫：以 `page.route` 讓 Developer 的 `/api/auth/me` 帶 `J3a:view`，跑 `Developer 看不到系統管理區` | **未執行**：同上（需真實 stack 完成註冊、核准與登入） | — |
| D1 | 6a 拿掉 `Sec-WebSocket-Protocol` 標頭（以 `deploy.yml` 的 `run` 原文抽出、刪除該行） | **對本機最小替身伺服器**（`127.0.0.1:8091`，有協定名標頭回 101＋協定名、否則 403；**不是** compose stack——本機 Docker daemon 未啟動）：exit=1，印出 `last round status line: HTTP/1.1 403 Forbidden`、`協定標頭：無`、`curl exit=0`。另以關閉的埠驗證網路失敗分支：exit=1、`(no status line)`、`curl exit=7`。第一次嘗試時以 shell 內嵌字串產生突變檔失敗（diff 為空），該次「exit=0」作廢、已重做 | 還原後對同一替身 exit=0（`HTTP/1.1 101 Switching Protocols`）；compose stack 上的正反案**未執行** |
| D2 | 6a 加 `continue-on-error: true` | `test_blocking_shape_without_token_or_secret` 紅 | 綠（4 案 OK） |
| D3 | 6a 移到 last-good 之後 | `test_position_between_redis_restart_check_and_last_good` 紅 | 綠 |
| D4 | 6a 複製進 `rollback` job | `test_not_copied_into_rollback_job` 紅 | 綠 |

**統計**：計畫列 59 道。已執行且紅 → 綠 55 道；**F1 執行後未紅**（如實記載理由）；**X1、X2 未執行**；D1 只對本機替身執行、未對 compose stack 執行。另補做閘道側等價突變 W1′、H1′、H3′ 三道（皆紅 → 綠）。

## 七、設計文字回補表（設計檔不回改，`team.md ## Corrections`）

| 設計檔與位置 | 原文 | 以何取代 | 依據 |
|---|---|---|---|
| `functional-spec.md` §二之一第 5 點 | 「若 `U13` 先於 `U14` 進 `ut`：C-8 必須隨 `U13` 一起出貨」 | ADR-0022 D-9 的論證（前端此前無消費者、同一次部署、不需升版）與合併前三項檢查 | functional-design R-07 |
| `functional-spec.md` §九之一 IAM 列 | 「不擴大可見範圍」（只對照擁有者範圍） | 擁有者範圍 ∩ `U23` 可見性（ADR D-2） | functional-design R-01 |
| `rules.md` `BR93.4` | Provider 以使用者 id 為 key 重掛 | 訂閱登入／登出事件、不帶 key | functional-design R-03 |
| `rules.md` `BR97.5` (2) | 自有且不同即改開（無條件） | 有未儲存內容時 `hold`、不回寫 | functional-design R-02 |
| `rules.md` `BR92.5` | 4403 → Navigate 到 `/` | 不導航、`refreshMe()` 至多一次、子頁面掛點依 K1 | nfr-requirements R-05；security-design §六之二 |
| `rules.md` `BR94.5` | 錨定「首次出現時該段最後一則大腦訊息」 | 最後一則是大腦訊息 → 錨定它；是使用者原句（伺服器先送 `work_items` 再送 token）→ 由該段下一則新建的大腦訊息承接 | 本站實作時查出（§九）；不改變「錨點不移動」的語意 |
| `performance-requirements.md` `EPN-06` | 每組 ≤ 4、快照 ≤ 12 | ≤ 5、≤ 15 | nfr-requirements R-02 |
| `performance-requirements.md` `EPN-02` | 理由「保護每 key 30 次握手」 | 「降低同秒重連」，支援 3 個分頁完整重試 | nfr-requirements R-07 |
| `performance-design.md` §三之一 ④' | 只有圖時以系統取專案再判可見性 | 移除（只有圖不推導、不判） | nfr-design R-01 |
| `performance-design.md` §三之三 | 「2 ＋ 5N」 | 「3 ＋ 3N（可見性 ＋1 常數）」；總數仍隨 N 線性 | nfr-design R-02 |
| `security-design.md` §二之二 | 「捕捉全部例外並記 log」 | `HierarchyForbidden` 不記 | nfr-design R-04 |
| `security-design.md` §七 M2 | (b) 會紅 | 由 V1 承接，(b2) 必紅 | nfr-design R-03 |
| `nfr-design-questions.md` 一第 3 項 | 「§五之二」 | `security-design.md` §六之二 | nfr-design R-07 |
| `cicd-pipeline.md` §三之二 | 「14 個」、「不受影響」含 `:55` | 15 個；`:55` 移出「不受影響」 | infrastructure-design R-01 |
| `infrastructure-specification.md` §二 PostgreSQL 列 | 「一次批次可見性查詢」 | 由 ADR D-5 的實例暫存落實（每實例每使用者一條 SQL） | nfr-design R-02 |
| `logical-components.md` §一之一 | `WorkTargetNames.owning_project_id: Optional[int]` | `project_ids: FrozenSet[int]` 與 `explicit: bool`（計畫 §一之一 #3 的形狀） | nfr-design R-06 |

## 八、StrictMode 的三項 code review（nfr-requirements R-04；檢查對象 `frontend/src/brain/useBrainConnection.ts`）

| # | 檢查 | 結果 |
|---|---|---|
| (a) | cleanup 一定關閉連線並清計時器 | 成立：cleanup 依序 `disposed = true` → `clearTimeout(timer)` → `dispatch(interruptOpenTurns, 'unmount')` → `ws.close(1000)` → `wsRef`／`connIdRef` 歸 null。事件回呼一律先檢查 `disposed || wsRef.current !== ws`，舊連線的 onclose 不會再排退避。突變 F26（cleanup 不關）使 E6 紅 |
| (b) | 不以 ref 去重 | 成立：effect 內沒有 `if (wsRef.current) return` 一類判斷；每次 setup 都 `new WebSocket(...)` 並以閉包內的 `disposed` 區分世代 |
| (c) | 沒有 effect 外建立連線的路徑 | 成立：`new WebSocket` 只出現在 effect 內的 `connect()`；退避計時器與「重新連線」鈕都只回到同一個 effect（計時器在 effect 閉包內呼叫 `connect()`；按鈕只 `setAttempt(n + 1)` 讓 effect 重跑） |

`vite dev` 下的雙重 effect 手動案不進 CI，交 `tcms-test-cases` 的「只能手動」桶。

## 九、實作期間查出並修正的缺陷（測試先紅，修正後綠）

| # | 症狀（e2e） | 根因 | 修正 |
|---|---|---|---|
| 1 | E28：快照先到時，開啟作業對象的圖之前送出了 `set_work_target{diagramId:'11'}` | bootstrap 的 `setCurrentDiagramId(11)` 在 `onPageReady` 之後才 commit；選定圖 effect 在對齊完成後看到 11 的「改變」而回寫 | 首次對齊把它判斷過的那張圖記為已處理（`lastDiagramRef`） |
| 2 | E34：刪除作業對象的圖後出現「作業對象已改為…」 | 自己送出的 `diagramId: null` 設定沒有被記為回聲 | 回聲比對鍵以空字串表示 null，刪除送出時一併記錄 |
| 3 | E37 間歇紅：評核頁回寫沒送出 | 清單回應剛到、`setDiagrams` 尚未 commit 的空窗內快照到達，鏡像中的清單仍為空 | 回寫判斷時鏡像查不到該圖就改用 `onPageReady` 傳入的清單；E37 單獨連跑 5 次、同步類 10 案連跑 3 次、全套 2 次皆綠 |
| 4 | E21：成本卡片排在工作項清單之上 | 伺服器在交辦時先送 `work_items` 再送 token，此時沒有本輪的大腦訊息可錨定 | `BR94.5` 的解讀補強（§七）：由該段下一則新建的大腦訊息承接 |
| 5 | Step 11 grep：零內容 `done` 沒有 `console.warn`（`BR93.2`） | 實作遺漏 | 補上（只含 turnId） |

## 十、交給 `build-and-test` 與 `tcms-test-cases` 的事項

| 事項 | 承接 |
|---|---|
| 對 `docker-compose.test.yml` stack 執行 `entry-page-live.spec.ts`（5）、`regression.spec.ts`、`estimate-workspace.spec.ts`（既有 15 案處置後） | `build-and-test`（本站未執行） |
| 突變 X1、X2（以 `page.route` 單案注入）與步驟 6a 對 compose stack 的正反案（D1） | `build-and-test`／`tcms-test-cases` 的 `automation-test-plan.md` |
| Kiwi 孤兒案例「身分驗證 › 管理員登入後進入工作區」：在 Kiwi UI 人工停用，記入 `tcms-sync-report.md`（infrastructure-design R-04） | `tcms-test-cases` |
| `vite dev` 下 StrictMode 雙重 effect 不留殭屍連線的手動案 | `tcms-test-cases`「只能手動」桶 |
| 真實 backend 重啟（`AC2.1.4`）：攔截層以 1011 重連驗證，真實重啟只能手動 | `tcms-test-cases`「只能手動」桶 |
| 部署後人工四步（`DEPLOY.md` §5.13；`cicd-pipeline.md` §五之二 第 1–4 步）；未完成第 1、4 步不得宣稱 `OPEN-EP14-13`／`OPEN-GW13-6` 結案 | 維運者，結果記入 `build-and-test` |
| 本 code-summary 的突變表（§六）轉入 `automation-test-plan.md`（`EPN-26`） | `tcms-test-cases` |
| 新增 54 案的 e2e 時間預算（`ui-regression` 15 分鐘）未量測；本機攔截層 49 案約 37 秒 | `build-and-test` |

## 十一、合併前檢查（只在分支上、squash 之前，由合併者執行；本站不執行合併）

1. `git log --oneline origin/ut..HEAD` 同時含 `U13` 與 `U14` 的 commit；
2. `grep -c projectName ws-contract.json` ≥ 1（本站寫入後為 2）；
3. `test -e backend/services/brain_router.py` 為假（本站確認不存在）。

任一不成立即停止合併（ADR-0022 D-9）。另：**使用者**須以 `gh api repos/<owner>/<repo>/actions/secrets` 與同路徑 `/variables` 各查一次，確認 `OPENROUTER_API_KEY` 在 secrets 而不在 variables（計畫 §七 第 4 點）。

## 十二、ADR-0006 四面向與揭露

| 面向 | 判定 | 本站落點 |
|---|---|---|
| IAM | 適用（擴充） | 名稱、目錄、直接設定三條路收緊為「擁有者範圍 ∩ 可見性」（ADR D-2–D-6）；`S2`／`S3` 擴及四個讀取方法、例外恰一筆；`brain_gateway.py` 不 import 任何成員關係符號（`test_brain_gateway_limits` 綠）；子頁面無 `K1` 不掛大腦掛點；前端 `K1` 判斷只是呈現 |
| Encryption | 適用（相同） | 零新傳輸、零新持久化；對話紀錄只在記憶體（E45 斷言鍵集合不變、值不含原句） |
| Network exposure | 適用（相同） | 零新端點、零新埠；6a 只送不帶身分的升級請求；4403 不再造成重連或導航迴圈（E10、E11） |
| Audit logging | 適用（相同；依 nfr-design R-04 更正） | 不新增稽核事件；新增一筆白名單內 WARNING `work_target_names_failed`（只帶 `connId`、例外類別名）；`HierarchyForbidden` 不記；前端 console 只帶 type／code／關閉碼／turnId（E46） |

**PBT**：不適用（非 IaC generator、cost calculator、agent routing），以窮舉身分的 example-based 測試驗證。

**揭露清單（計畫 §七 與本站新增）**：

1. 目錄總語句數仍是 3 ＋ 3N（N ≤ 50；`CatalogStatementCountTest` 鎖住）：可見性成本為常數，逐專案 `list_systems` 的三條是 `U13` 既有成本；若要總數常數需另開工作（新增批次列舉方法），本站未做。`MembershipFacade.project_visibility` 改為實例暫存，改到 `U19`／`U23` 的一個方法（閉包語意不變，`U23` 四支測試綠）。
2. 偏離 `BR92.5` 字面：4403 不導航；`refreshMe()` 是 `EPN-08`「零 HTTP」唯一例外（既有端點、只在終止路徑）。
3. 重開 `U2`／`U7`／`U13`／`U19`／`U23`：既有斷言只補參數，唯一改期望的是 `test_brain_gateway_startup.py:60` 的 lambda（計畫允許）。
4. **協定名字面**：Step 11 grep `cloud360.brain.v1` 在 `frontend/src` 的唯一命中是產生檔 `src/types/ws-contract.d.ts`（`WsSubprotocol.protocolName` 的字面型別，無法避免）；本單元程式以受字面型別約束的 template literal 組出協定名（`brainProtocol.ts`），型別錯誤時 tsc -b 紅（已實測：改為 v2 即 TS2322）。
5. 新增計畫 §八 表外的 testid（皆 `brain-` 前綴）：`brain-live`、`brain-conversation`、`brain-user-message`、`brain-workitem-list`、`brain-context-none`、`brain-context-sharing-switch`、`brain-transcript-remembered`、`brain-empty-state`、`brain-reconnect`、`brain-relogin`；`brain-stream-message` 另帶 `data-turn-id`／`data-status`。
6. 攔截層與計畫字面的差異：E30 的「先拒握手、再接受」改為「握手完成但快照由測試控制送出時機」（等價的晚到快照，時序可決定）；E43 的「/me 回 500」改為「/me 回應缺 id」——/me 回 500 時使用者沒有任何權限、無法對話，案例不可構造；要測的資料狀態（user 無 id）相同，且突變 F5 確實使它紅。
7. G6 還原後首輪 `test_brain_gateway_limits.RateLimitTest.test_per_user_message_limit_spans_tabs_and_survives_reconnect` 紅過一次；之後全模組連跑 6 次、該 class 單獨 25 次皆綠。原因未定位（該測試以真實時間輪詢連線登錄釋放，本單元在握手中多了一次 `to_thread`），列為**偶發、未排除與本單元有關**。
8. `DEPLOY.md` 仍保有既有的 `## 中文版`／`## English Version` 分段；本站只新增 §5.13，未整理既有分段（不在本單元範圍）。
9. 本機無 Docker：真實 stack 層、既有 15 案、X1、X2、D1（compose）皆未執行，**不宣稱綠**。

## 十三、既有 15 個 e2e 的處置核對（code review：只改落點斷言與註解，未放寬其他斷言）

`git diff` 的程式行（註解除外）只有下列變更：

| 測試 | 舊落點斷言 | 新斷言 | 其後的正向錨點 |
|---|---|---|---|
| 錯誤密碼被拒並停留在登入頁 | `not.toHaveURL(/\/workspace/)` | `toHaveURL(/\/login$/)` | 錯誤訊息可見（既有） |
| 管理員登入後進入入口頁（原名「…進入工作區」） | `toHaveURL(/\/workspace/)`＋「架構」鈕 | `toHaveURL(/\/$/)` | `brain-entry-page` 可見 |
| 登出後返回登入頁 | `toHaveURL(/\/workspace/)` | `not.toHaveURL(/\/login$/)` | 新增「登出系統」可見（隨即點擊，既有） |
| Platform_Admin 看得到系統管理區 | 同上 | 同上 | 「系統管理」可見（既有） |
| Developer 看不到系統管理區（admin 段） | 同上 | 同上 | 前往審核頁後的列可見（既有） |
| Developer 看不到系統管理區（Developer 段） | 同上 | 同上 | **新增** `sidebar-entry-link` 可見，再 `toHaveCount(0)` |
| `gotoAdmin`（8 案共用） | 同上 | 同上 | 「使用者角色」heading 可見（既有） |
| `estimate-workspace` 的 `login` helper 與 `:35`（2 案） | `toHaveURL(/\/(workspace\|cost)/)` | `not.toHaveURL(/\/login$/)` | 其後 `/cost` 斷言（既有） |

seed 角色 `Platform_Admin` 與 `Developer` 皆具 `K1 view`（`rbac_seed_data.py:317`、`:325`），故兩者的正向錨點成立。

## 十四、ADR 與完成條件

- `inception/decisions/0022-work-target-names-and-brain-read-visibility.md` 由草案原樣移入，只改 Status 行與標題；以 diff 確認兩者除這兩處外完全相同。
- `LOCAL-DEV.md`：**不觸發**（未改 `database.py` 的 schema 補丁、`nginx.conf`、任一 `.env.example`、`render-env.sh`）。
- schema ↔ deploy 同步：**不觸發**（零 DDL、零 seed 變更；`describe_work_target` 為純查詢）。
- `grep -n "入口頁部署後實測" DEPLOY.md` 命中 §5.13；`validate_repo_contract.py` 通過。
- 計畫 §一之五「不改的檔」：`git diff --stat` 全為零變更；新檔路徑不含 `prod`／`production`／`secrets` path part。

## 十五、Step 11 grep 完成條件（逐筆判讀）

| 條件 | 命中 | 判讀 |
|---|---|---|
| `localStorage\|sessionStorage\|indexedDB\|caches\.`（`EPN-13`） | 1：`brainTranscript.ts:7` | 檔頭註解（「不寫 localStorage／…」），非程式 |
| `4000`（`EPN-27`） | 0 | — |
| `fetch(`（`EPN-08`） | 0 | — |
| app 程式匯入 `brain/testing` | 0 | — |
| `key=`（`App.tsx`、`BrainTranscriptContext.tsx`） | 0、0 | — |
| `projectName` 型別宣告 | 宣告只在 `ws-contract.d.ts:339`；其餘 4 處為讀取（`ContextBar.tsx`、`brainProtocol.ts`）與建構器參數（`wsFrames.ts`） | 符合 `NFR5.140` |
| `cloud360.brain.v1\|'bearer\.'` | 1：`ws-contract.d.ts:462`（產生檔） | 見 §十二 第 4 點 |
| `console.`（`src/brain`、`components/brain`、`EntryPage.tsx`） | 5：malformed frame、ignored message type（兩處）、connection closed（關閉碼）、empty turn（turnId） | 皆只帶 type／關閉碼／turnId，不含 payload |
