# Code Summary — `U15 memory-page-ui`


## 一、檔案

| 動作 | 檔案 |
|---|---|
| 新建 | `frontend/src/pages/MemoryPage.tsx` |
| 新建 | `frontend/src/components/memory/{MemoryZone,MemoryItem,DeleteConfirmRow,EpisodicPager}.tsx` |
| 新建 | `frontend/src/memory/{memoryApi,memoryPaging,memoryEntry,memoryLabels}.ts` |
| 新建 | `frontend/tests/e2e/memory-page.spec.ts`（10 個案例，`describe`：`U15 memory page`） |
| 新建 | `backend/tests/test_memory_pending_authz.py`（7 個案例） |
| 修改 | `frontend/src/App.tsx`（`/memory`，只包 `ProtectedRoute`） |
| 修改 | `frontend/src/components/Sidebar.tsx`（「我的記憶」，位於 DEMO SCOPE 區塊之後的獨立 `<div>`） |
| 修改（跨單元，`U8`） | `backend/services/hierarchy_facade.py`（`Principal.is_approved`，由 `rbac.user_is_approved` 填入） |
| 修改（跨單元，`U8`） | `backend/services/memory_facade.py`（`_authorize_approved`，六個公開方法的第一行） |
| 修改（跨單元，`U8`） | `backend/services/memory_errors.py`（僅 docstring：`pending` 理由） |
| 修改（跨單元，`U8`） | `backend/services/memory_router.py`（`DELETE`、`POST` 宣告 403；router 仍不做授權判定，`C3` 綠） |
| 重新產生 | `openapi.json`、`frontend/src/types/api.d.ts`（只多兩個 403 宣告與 docstring） |

## 二、關鍵決定

- **已核准檢查落在 facade**：涵蓋 HTTP 與同進程（`intent_routing.py`）兩條路徑；判定先於取列，故 pending 帳號刪除不存在的 id 也是 403，不構成存在性 oracle。`intent_routing.py` 已會攔下該例外並在無記憶下繼續。
- **補償重抓**：情節區刪除後背景重抓目前頁，以 `useRef` 序號比對防亂序（沿用 `AdminPage.tsx:124-131` 的真正機制）；失敗時顯示「清單同步失敗」並播報。
- **單一退頁者**：只由補償重抓的回應決定是否退頁。
- **`hasNext` 保留至下一次伺服器回應**：避免本地刪除移除探測列後「下一頁」在重抓期間被誤停用。

## 三、對計畫的偏離（皆有理由，無一降低驗證強度）

| # | 偏離 | 理由 |
|---|---|---|
| 1 | e2e E6 刪兩則而非一則 | 第 1 頁以 `limit=21` 取得，第 21 筆已在本地；刪一則時不重抓也會顯示它，「移除重抓」的突變會綠燈。刪兩則時第 22 筆只能經重抓取得 |
| 2 | e2e E8 刪空第 3 頁（41 則） | 由第 2 頁退回第 1 頁無法區分「退一頁」與「跳回第一頁」 |
| 3 | `hasNext` 保留伺服器最後值 | 見 §二 第 4 點；否則 E7 無法執行 |
| 4 | 兩個 API 函式第一個參數為 `token` | 與 `membershipApi.ts` 一致；計畫的簽章省略了它 |
| 5 | `memoryPaging.ts` 多匯出 `episodicOffset`、`EPISODIC_PROBE_LIMIT` | 讓 offset 與 limit 由常數推導 |
| 6 | 兩個不在已核可清單的 test id：`memory-zone-episodic-sync-failed`、`memory-page-identity-error` | 承載計畫 §二 的同步失敗提示與 `/me` 失敗錯誤態 |
| 7 | 情節區的計數標示為「目前 offset ＋ 畫面列數」，有下一頁時加「+」 | 計畫未規定；與「不宣稱總數」一致 |
| 8 | e2e E1 由 `/brain` 起步 | 測試帳號無 story 權限，`/` 會導向 `/403`（無 Sidebar） |
| 9 | `BR34.4`「不發任何重抓」的偏離 | 計畫 §二 已核可：情節區刪除後背景重抓。`rules.md` 依 `refined-mockups:c3` 不回改，偏離記於此 |
| 10 | `memory_router.py` 的 `POST` 也新增 403 宣告 | 已核准檢查同樣作用於建立；計畫只點名 `DELETE` |
| 11 | **已核准檢查的落點由 nfr-design `security-design.md §四` 的「router 層 dependency」改為 facade 六個公開方法的第一行**，並連帶改動 `U8` 已完成的 `memory_facade.py`、`memory_errors.py`（新增 `reason="pending"`）與 `memory_router.py` 的 OpenAPI 回應集合 | router 契約宣告本層不做授權（`memory_router.py:8-12`，`C3` 斷言），且 `intent_routing.py` 同進程直呼 facade。此改動擴大了 `K-08` 已核可契約的 `MemoryForbidden.reason` 集合與 `DELETE` 的 403 宣告，**需在下一輪契約修訂與 `D8-1`／`D8-2` 一併追認** |
| 12 | 修補輪新增的 e2e E11–E15 與後端 B8、B9 未列入 `unit-test-instructions.md` | 該檔為已核可內容，改動會使 Plan Approval 失效；新增案例記於本檔 §七 |

## 四、測試結果

| 指令 | 結果 |
|---|---|
| `cd backend && python3 -m unittest tests.test_memory_pending_authz -v` | 7/7 |
| `cd backend && python3 -m unittest tests.test_memory_authz tests.test_memory_contract` | 41/41，`C3` 綠 |
| `cd backend && python3 -m unittest discover -s tests` | 736/740；4 個失敗皆在 `test_progress_channel_contract`，指向本機另一個被 `.git/info/exclude` 排除的 worktree（`.kilo/worktrees/secret-deposit/`），CI 看不到，與本單元無關 |
| `python3 backend/scripts/dump_openapi.py --check`；`npm run check:types` | 一致 |
| `npm run lint` | 0 error（2 個 warning 在本單元未碰的檔案） |
| `npm run build`（含 `tsc -b`） | 通過 |
| 新增檔案 grep `localStorage`／`sessionStorage`／`IndexedDB`／`dangerouslySetInnerHTML` | 各 0 |
| `npx playwright test tests/e2e/memory-page.spec.ts`（對 production build 的 `vite preview`） | 10/10；`--repeat-each=5` 50/50 |
| 連同 `member-pages.spec.ts` | 20/20 |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/memory-page.spec.ts` | 10 案、0 ERROR、0 WARN |
| `validate_env_contract.py`、`validate_repo_contract.py` | 通過 |

**未在本機執行**：`regression.spec.ts`（需要完整 docker stack，由 `ui-regression` 涵蓋）。

## 五、突變驗證（每項：套用→確認紅→還原→確認綠）

| 突變 | 紅燈案例 |
|---|---|
| facade 已核准檢查改為 no-op | B1–B4、B6 |
| `delete` 在取列之後才檢查 | B3（回 404） |
| `mint_principal` 一律 `is_approved=True` | B1–B4、B6、B7 |
| 檢查反轉（拒絕 approved） | B1–B6 |
| `canSeeMemoryEntry` 回 false | E1 |
| 探測 `limit` 改為 20 | E2 |
| 區塊錯誤設成 `empty` | E3 |
| 每列 `canDelete={true}` | E4 |
| 停用 Escape | E5 |
| 移除背景重抓 | E6 |
| 移除重抓的序號比對 | E7（舊回應以「第 1–20 則」蓋掉第 2 頁） |
| 隱藏同步失敗提示 | E8 |
| 退頁直接跳回第 1 頁 | E8 |
| 內容以 raw HTML 渲染 | E9 |
| 失敗時 log `record.content` | E10 |

## 六、交接事項

| 事項 | 承接者 |
|---|---|
| `HierarchyFacade._authorize` 呼叫 `user_can(db, role, "K2", action)` 時未傳帳號核准狀態，有角色的 pending 帳號不會被擋（與本單元修補的同類缺口） | 本單元範圍外；於核可關卡提交使用者決定承接方式 |
| `K-08` 契約追認：`MemoryForbidden.reason` 新增 `pending`、`DELETE`／`POST` 新增 403 宣告（偏離 #11） | 下一輪契約修訂，與 `D8-1`／`D8-2` 同批 |
| `U14 entry-page-ui` 的入口頁捷徑須匯入 `frontend/src/memory/memoryEntry.ts` 的 `canSeeMemoryEntry`（INV-3、`OPEN-MP15-1`） | `U14` 的 code-generation |

## 七、修補輪（程式審查後，使用者裁決當下修正）

| 審查發現 | 修正 | 新測試 |
|---|---|---|
| R-01 刪除進行中翻頁：舊頁碼閉包使使用者被拉回、補償失敗時整區卡在載入 | `MemoryZone.tsx` 以三個 ref 追蹤目前頁次、目前頁是否載入成功、在途頁載入的目標；刪除完成後只重抓使用者**現在**所在的頁，有在途頁載入時改經 `loadPage` 重送（失敗必落在可重試的 `error`）；只在被刪列仍在畫面上時才移動焦點 | E11、E12 |
| R-02 `search` 的已核准守衛無測試 | — | B8（pending principal 呼叫 `search` → `MemoryForbidden(pending)` 且 `embed` 呼叫 0 次；approved 則恰 1 次，證明觀察點有接上） |
| R-03 `UIP-*` 追溯過度宣稱 | 追溯逐列改寫；`UIP-4` 改標 Deferred（部分覆蓋，理由見追溯檔） | E13（`UIP-1`）、E14（`UIP-4` 的守衛）、E15（`UIP-6`） |
| R-04 預設放行 | 維持預設，以測試鎖住語意 | B9（`authorization_status` 為 None 或缺欄位 → `is_approved=True`） |

修補輪的突變驗證（每項套用→紅→還原→綠）：

| 突變 | 紅燈 |
|---|---|
| 移除 `search` 的 `_authorize_approved` | B8 |
| `mint_principal` 改為 fail-closed | B9（B7 仍綠，證明 B9 非重複） |
| 還原舊的 `handleRemoved` | E11、E12 |
| 無條件移動焦點 | E11 |
| 改用 `resyncInBackground` 而非 `loadPage` 重送 | E12 |
| 三區依序掛載；全部完成才顯示 | E13 |
| 移除「下一頁」的載入中停用 | E14 |
| 以點擊當下的 `items` 而非 `prev` 過濾 | E15 |

修補輪測試結果：後端 43/43（含 B8、B9）；`npm run lint` 0 error；`npm run build` 通過；e2e 15/15、`--repeat-each=5` 75/75；`tcms_validate --spec` 15 案、0 ERROR、0 WARN。

**R-05（專案／成員服務的同類缺口）**：仍為交接事項，承接方式於核可關卡交使用者決定。

## 重新查驗與合併前必修第 6 項

> 記錄時間：2026-10-23T12:09:55Z（`date -u`）。來源：code-generation 整站 Request Changes；本單元承接 `functional-design/merge-blockers.md` 第 6 項（`review-02` R-08），使用者裁決「收到 404 就重新讀清單確認」（計畫 §四之一）。

### 一、Steps 1–12 重新查驗

| Step | 判定 | 查證方式 |
|---|---|---|
| 1 | 成立 | `frontend/src/memory/`（4 檔）、`frontend/src/components/memory/`（4 檔）存在 |
| 2 | 成立 | `tests.test_memory_authz` 可載入且綠；spec 檔已存在，`--list` 的「0 個」條件已不適用（現為 18 案） |
| 3 | 成立 | `hierarchy_facade.py:63` import `user_is_approved`、`:166` `is_approved: bool = True`、`:188` 由 `mint_principal` 填入；`memory_facade.py` 六個公開方法首行呼叫 `_authorize_approved`（:272、:315、:352、:393、:429、:486），`REASON_PENDING`（:109） |
| 4 | 成立 | `tests.test_memory_pending_authz` 存在並綠（見下方指令輸出） |
| 5 | 成立 | `memory_router.py:88` `FORBIDDEN_RESPONSE`，檔頭 :29-42 已說明 403 來自身分 |
| 6 | 成立 | `dump_openapi.py --check`、`npm run check:types` 皆一致 |
| 7 | 成立（本輪改動 `memoryApi.ts` 的 404 語意，見二） | 四個模組存在 |
| 8 | 成立 | `App.tsx:113` `/memory`、`Sidebar.tsx:245-248` `sidebar-memory-link`，以 `canSeeMemoryEntry` 判定 |
| 9 | 成立 | lint 0 error；build 通過；四個關鍵字在本單元檔案 grep 0 命中 |
| 10 | 成立 | e2e 18/18（含本輪新增 3 案） |
| 11 | 成立 | 兩支 contract validator 通過 |
| 12 | 成立 | 本檔、`source-manifest.json`、`traceability.json` 存在 |

**本輪其他單元改過的共用檔對本單元判準的影響**（如實記錄，本單元未改這些檔）：

| 共用檔 | 改動 | 影響 |
|---|---|---|
| `hierarchy_facade.py` | `HierarchyFacade._authorize` 首行加 `if not principal.is_approved: raise HierarchyForbidden`（2026-10-20） | 本檔 §六 第一列交接事項「`HierarchyFacade` 同類缺口」**已由 hierarchy-service 修正**，不再是待承接事項；`Principal.is_approved` 的讀者由一個變兩個，本單元的 B7／B9 語意不變 |
| `intent_routing.py` | `_memory_notes` 對 `MemoryForbidden` 原樣向上傳遞（合併前必修第 13 項） | 本檔 §二 第一點「`intent_routing.py` 已會攔下該例外並在無記憶下繼續」**已不成立**：現為以授權錯誤結束該輪。本單元 B6（同進程直呼 facade raise `MemoryForbidden`）不受影響，仍綠 |
| `user_router.py` | 硬刪除預檢會計數 `memory_records`／`memory_audit_events` | 不觸及本單元的判準；本單元後端測試全綠 |
| `memory_facade.py` | 本輪無工作樹改動（最後改動為本單元的 `8cf948c`） | — |

### 二、Step 13 實作

| 檔:行 | 改動 |
|---|---|
| `frontend/src/memory/memoryApi.ts:85-91` | 新增型別 `DeleteMemoryOutcome = 'deleted' \| 'not-found-unconfirmed'` |
| `frontend/src/memory/memoryApi.ts:120` | 404 回 `'not-found-unconfirmed'`（原為 `'already-gone'`）；檔內 docstring 改寫為「404 不等於已刪除」 |
| `frontend/src/components/memory/MemoryZone.tsx:77-80` | 兩則失敗文字常數 `STILL_LISTED_TEXT`、`UNCONFIRMED_TEXT` |
| `frontend/src/components/memory/MemoryZone.tsx:230-245` | `deleteRecord(memoryId, rowPage)`：204 → `'deleted'`；待確認 → 以 `fetchMemoryRecords(token, kind, offsetFor(rowPage), limit)` 重讀；不含該則 → `'already-gone'`（既有移除＋播報路徑）；仍含 → 拋 `STILL_LISTED_TEXT`；重讀失敗 → 拋 `UNCONFIRMED_TEXT` |
| `frontend/src/components/memory/MemoryZone.tsx:364` | 傳入 `MemoryItem` 時綁定該列所在頁 `page` |
| `frontend/src/components/memory/MemoryItem.tsx:45-50、:90` | 僅註解：`deleteRecord` 的 `'already-gone'` 改為「經重讀確認」 |
| `frontend/tests/e2e/memory-page.spec.ts:882-985` | 新增 3 案（含結構化規格註解），既有 15 案名稱未改 |

設計要點：確認重讀是**純確認**——不遞增 `requestSeq`、不寫入任何 state，列表落地仍只經 `applyLoaded`，故不與翻頁、背景重抓互相覆蓋；`MemoryItem` 的失敗分支（`failed` 狀態、`刪除失敗：…` 文字與播報、焦點回到刪除鍵）原樣沿用。資料抓取仍是「純抓取函式 ＋ 呼叫端 callback」兩層，無 effect 內 setState。後端未改、不依賴錯誤訊息字串。

### 三、測試與突變

新增案例（計畫與 `unit-test-instructions.md §四之三` 編為 E11–E13，與 §七 修補輪既有的 E11–E15 撞號；spec 註解以 `MB6-E11`…`MB6-E13` 區分）：

| 編號 | 案例名稱（TCMS 名稱的 test 段，落地後不可改） |
|---|---|
| MB6-E11 | `a 404 delete counts as deleted only after a re-read no longer lists the record`（語意區；斷言 404 後恰多 1 個 `kind=semantic、limit=200、無 offset` 的 GET，該列消失並播報） |
| MB6-E12 | `a 404 delete whose re-read still lists the record fails and keeps the row`（情節區第 2 頁；斷言重讀為 `offset=20、limit=21`，該列保留並顯示「刪除失敗」） |
| MB6-E13 | `a 404 delete whose re-read fails is reported as a failure and keeps the row`（語意區；重讀 500，該列保留、區塊不進錯誤態） |

突變（每項：套用→重建→紅→還原）：

| 突變 | 結果 |
|---|---|
| M1：「404 一律 `'already-gone'`」（待確認即回 `'already-gone'`，不重讀） | MB6-E11、E12、E13 三案皆紅（E11 因少了確認 GET 而紅；E12 為計畫指定的紅燈案例） |
| M2：重讀失敗視同已刪除 | 僅 MB6-E13 紅 |
| M3：重讀仍列出也視同已刪除 | 僅 MB6-E12 紅 |

M2 第一次套用時 `tsc -b` 因未使用常數失敗、建置未更新，該次結果作廢；改寫突變使建置成功後重跑，以上為有效結果。三項還原後全套重跑綠（見下）。

### 四、各命令實際輸出

| 指令 | 輸出 |
|---|---|
| `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_memory_pending_authz tests.test_memory_authz tests.test_memory_contract` | `Ran 43 tests` / `OK` |
| `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests` | `Ran 1269 tests in 96.662s` / `OK (skipped=3)` |
| `python3 backend/scripts/dump_openapi.py --check` | `規格檔與後端程式碼一致。` |
| `npm run check:types` | `API 型別檔與規格檔一致。` |
| `npm run lint` | `✖ 2 problems (0 errors, 2 warnings)`（兩個 warning 不在本單元檔案，`WorkspacePage.tsx:344` 等） |
| `npm run build` | `✓ built in 492ms`（chunk 大小 warning 為既存） |
| `npx vite preview --port 4187 --strictPort`（背景）＋ `BASE_URL=http://localhost:4187 npx playwright test tests/e2e/memory-page.spec.ts` | `18 passed (18.5s)` |
| 同上 `--repeat-each=5` | `90 passed (1.5m)` |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/memory-page.spec.ts` | `通過 18/18　ERROR 0　WARN 1` |
| `python3 scripts/validate_env_contract.py`、`python3 scripts/validate_repo_contract.py` | 皆 `validation passed` |

preview 伺服器跑完即停止。最後一次 e2e 之後，`MemoryZone.tsx` 只改了一段註解（已接受風險的措辭），lint 與 build 已重跑通過，e2e 未再重跑。

**WARN 判讀**：MB6-E13 的 `@api GET /api/memory/records -> 500` 不在 OpenAPI 宣告集合（200／403／422）內。500 在此模擬的是基礎設施或代理層失敗（確認重讀本身失敗），不是端點宣告的行為；依指示不改後端，故不補 `responses=`，WARN 保留。

### 五、已接受風險

只重讀該列所在的那一頁。兩次請求之間若有更早的記憶被刪除使清單位移，該則可能滑到前一頁而被誤判為已刪除；機率低，且後果與裁決前（404 一律視為已刪除）相同。情節區探測列 `limit=21` 只涵蓋「往後」位移一筆，不涵蓋此情境。

### 六、偏離與未驗項

| # | 項目 | 說明 |
|---|---|---|
| 1 | 「當前頁」的詮釋 | 計畫寫「該區目前這一頁」。實作取**該列被渲染時畫面上的頁**（按下確認那一刻的頁），而非 404 回應到達時的頁：刪除在途時使用者若翻頁，以新頁重讀必然不含該則，會誤判為已刪除。通常兩者相同 |
| 2 | 編號撞號 | 計畫的 E11–E13 與 §七 既有 E11–E15 撞號，以 `MB6-` 前綴區分；`unit-test-instructions.md` 為已核可內容，未改 |
| 3 | `source-manifest.json` 未改 | 本輪寫入的四個檔（`memoryApi.ts`、`MemoryZone.tsx`、`MemoryItem.tsx`、`memory-page.spec.ts`）皆已在既有條目（`frontend/src/memory/`、`frontend/src/components/memory/`、spec 檔）涵蓋範圍內，無新路徑 |
| 4 | 未驗 | `regression.spec.ts` 與 `ui-regression` 完整 stack（需 docker）；真實後端的 404 情境（本單元 e2e 全以 `page.route()` 攔截） |
| 5 | 文件過期 | 本檔 §二 第一點（`intent_routing.py` 降級）與 §六 第一列（`HierarchyFacade` 交接）已被其他單元的改動推翻，見一之表；原文不回改 |

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T15:11:36Z -->

本輪只查驗、未改任何程式或測試。計畫 17 格全部勾選（機械計數：`[x]` 17、`[ ]` 0）。Step 2 的「spec 尚不存在時 `--list` 回 0」因 spec 早已存在而無法重現，以執行器可用（後端三檔 43 OK、Playwright 收集 18 案）判定。

測試與檢查（本機實跑）：後端完整套件 1319 OK（skipped 3；log 中 23 行 `ERROR:` 皆為 logger 輸出）；單元範圍 `test_memory_pending_authz`／`test_memory_authz`／`test_memory_contract` 43 OK；`npm run lint` 0 errors、2 個既有 `exhaustive-deps` warning（非本單元）；`check:types` 一致；`tsc -b` 通過（只更新既有且已 gitignore 的 `node_modules/.tmp/*.tsbuildinfo` mtime）；`vite build` 輸出到 scratchpad 成功。e2e：以 `vite preview` 服務 scratchpad 建置實跑 `memory-page.spec.ts` **18/18 passed**（`--reporter=list`、`--output` 指到 scratchpad），跑完已停。兩支 contract validator 通過。突變未重跑，沿用本檔 §五、§七、「重新查驗」§三。git status（含 `--ignored`）前後無新增。

合併前必修 **#6 屬實已解決**：`memoryApi.ts:119-120` 只有 204 回 `'deleted'`，404 回 `'not-found-unconfirmed'`，其他狀態碼拋例外；`MemoryZone.tsx:230-244` 收到 404 後以該列所在頁的同一組參數重讀（不動 `requestSeq`、不寫 state）：已不含該則 → 走 204 的移除與播報路徑；仍含 → 拋 `STILL_LISTED_TEXT` 保留該列；重讀失敗 → 拋 `UNCONFIRMED_TEXT` 保留該列。三個 e2e（`:899`、`:934`、`:966`）本輪綠，`:934` 斷言重讀參數為 `offset=20`、`limit=21`。已接受風險（重讀只看一頁，位移超過一筆時可能誤判）見第 6 列補記 (a)。

已核可計畫／測試說明與程式的落差（不回改計畫）：Step 8 的「放在 `Sidebar.tsx:209-216` DEMO SCOPE 區塊之後」——該區塊已由後續單元移除，現位於「專案」之後、管理區之前，符合線框 §14；Step 3 的「`HierarchyFacade` 不改」——`hierarchy_facade.py:214` 已有 `is_approved` 拒絕（hierarchy-service review-01，2026-10-20）；Step 7 的 `fetchMemoryRecords` 多一個 `token` 參數，404 處置已由 Step 13 取代；`unit-test-instructions.md` 寫後端 7 案、e2e 10＋3 案，實為 9 案與 18 案（E11–E13 與修補輪撞號，spec 以 `MB6-` 註解區分）；測試說明的本機指令用 `python3` 與裸 `npx playwright`，預設 reporter 會寫出 `frontend/pw-report.json` 與 `junit.xml`。

候選問題（未修，交審查判定）：member-pages-ui 的兩種形狀在本單元不適用（`/memory` 無路由參數，`/me` 失敗有 `memory-page-identity-error`；本單元無 dialog，`DeleteConfirmRow` 為就地 `role="group"`，有 Escape 取消與焦點歸還）。(1) 刪除送出期間確認列卸載、刪除入口 `disabled`，焦點掉到 `body`；成功時情節區只在被刪列位於目前頁時才移焦點。(2) Sidebar「我的記憶」的 `<nav>` 沒有 `aria-label`，旁邊「專案」的有，可能觸發 axe `landmark-unique`。
