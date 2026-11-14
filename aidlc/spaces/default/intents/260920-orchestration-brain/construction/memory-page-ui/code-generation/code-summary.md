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
  > **就地標註（2026-10-31，review-03 R-05）**：本點最後一句**已被推翻**——合併前必修第 13 項使 `intent_routing.py` 的 `_memory_notes` 對 `MemoryForbidden` 原樣向上傳遞（以授權錯誤結束該輪），不再「在無記憶下繼續」。依據見「重新查驗與合併前必修第 6 項」§一 的共用檔表。原文保留。
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

> **就地標註（2026-10-31，review-03 R-05）**：上表第一列**已不是待承接事項**——`hierarchy_facade.py` 的 `HierarchyFacade._authorize` 已於 2026-10-20 由 hierarchy-service 加上 `is_approved` 拒絕（見「重新查驗與合併前必修第 6 項」§一 的共用檔表）。原文保留。

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

> **就地補記（2026-10-31，review-03 R-02）**：上段只寫了「往前」位移。判定以 id 比對（`MemoryZone.tsx:235` `data.some((r) => r.memory_id === memoryId)`），誤判條件實為「該則離開了被重讀的那一頁」，故另有**往後**位移：情節區在兩次請求之間若有 2 筆以上新記憶寫入（agent 會寫入），該則被推出 `limit=21` 探測範圍，同樣被判為已刪除。誤判仍需「404 本身是假的」同時發生，機率低，嚴重度與上段相同。程式註解 `MemoryZone.tsx:226-228` 仍只寫往前位移（需改程式，記為已知限制，見本檔「共用檔異動後的重新驗證與補審」§四）。

### 六、偏離與未驗項

| # | 項目 | 說明 |
|---|---|---|
| 1 | 「當前頁」的詮釋 | 計畫寫「該區目前這一頁」。實作取**該列被渲染時畫面上的頁**（按下確認那一刻的頁），而非 404 回應到達時的頁：刪除在途時使用者若翻頁，以新頁重讀必然不含該則，會誤判為已刪除。通常兩者相同 |
| 2 | 編號撞號 | 計畫的 E11–E13 與 §七 既有 E11–E15 撞號，以 `MB6-` 前綴區分；`unit-test-instructions.md` 為已核可內容，未改 |
| 3 | `source-manifest.json` 未改 | 本輪寫入的四個檔（`memoryApi.ts`、`MemoryZone.tsx`、`MemoryItem.tsx`、`memory-page.spec.ts`）皆已在既有條目（`frontend/src/memory/`、`frontend/src/components/memory/`、spec 檔）涵蓋範圍內，無新路徑 |
| 4 | 未驗 | `regression.spec.ts` 與 `ui-regression` 完整 stack（需 docker）；真實後端的 404 情境（本單元 e2e 全以 `page.route()` 攔截） |
| 5 | 文件過期 | 本檔 §二 第一點（`intent_routing.py` 降級）與 §六 第一列（`HierarchyFacade` 交接）已被其他單元的改動推翻，見一之表；原文不回改 |

> **就地更正（2026-10-31，review-03 R-01、R-03）**：
> - **第 2 列陳述有誤**：`unit-test-instructions.md` **有改**——§四之三（E11–E13 三列與本機實跑說明，`:90-100`）於本輪加入並隨 `c6a40f9` 提交；2026-10-31 又加了第二節末的「現況註記」（`:52`）。該檔不是「未改」。
> - **編號對照**（同一組案例兩套名稱）：`unit-test-instructions.md §四之三` 的 E11／E12／E13 ＝ spec 註解與 `traceability.json` 的 `MB6-E11`（`memory-page.spec.ts:899`）／`MB6-E12`（`:934`）／`MB6-E13`（`:966`）。spec 內不帶前綴的 E11–E15 是修補輪的另一組（`:664`、`:710`、`:771`、`:815`、`:853`），與上述無關。
> - **第 1 列的設計選擇未被測試鎖住**（R-03）：三支 `MB6-` 案例都沒有「DELETE 在途時翻頁」的情境；若 `deleteRecord` 的 `rowPage` 改回讀目前頁，三案仍綠。補測試需改 spec，記為已知限制。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T15:11:36Z -->

本輪只查驗、未改任何程式或測試。計畫 17 格全部勾選（機械計數：`[x]` 17、`[ ]` 0）。Step 2 的「spec 尚不存在時 `--list` 回 0」因 spec 早已存在而無法重現，以執行器可用（後端三檔 43 OK、Playwright 收集 18 案）判定。

測試與檢查（本機實跑）：後端完整套件 1319 OK（skipped 3；log 中 23 行 `ERROR:` 皆為 logger 輸出）；單元範圍 `test_memory_pending_authz`／`test_memory_authz`／`test_memory_contract` 43 OK；`npm run lint` 0 errors、2 個既有 `exhaustive-deps` warning（非本單元）；`check:types` 一致；`tsc -b` 通過（只更新既有且已 gitignore 的 `node_modules/.tmp/*.tsbuildinfo` mtime）；`vite build` 輸出到 scratchpad 成功。e2e：以 `vite preview` 服務 scratchpad 建置實跑 `memory-page.spec.ts` **18/18 passed**（`--reporter=list`、`--output` 指到 scratchpad），跑完已停。兩支 contract validator 通過。突變未重跑，沿用本檔 §五、§七、「重新查驗」§三。git status（含 `--ignored`）前後無新增。

合併前必修 **#6 屬實已解決**：`memoryApi.ts:119-120` 只有 204 回 `'deleted'`，404 回 `'not-found-unconfirmed'`，其他狀態碼拋例外；`MemoryZone.tsx:230-244` 收到 404 後以該列所在頁的同一組參數重讀（不動 `requestSeq`、不寫 state）：已不含該則 → 走 204 的移除與播報路徑；仍含 → 拋 `STILL_LISTED_TEXT` 保留該列；重讀失敗 → 拋 `UNCONFIRMED_TEXT` 保留該列。三個 e2e（`:899`、`:934`、`:966`）本輪綠，`:934` 斷言重讀參數為 `offset=20`、`limit=21`。已接受風險（重讀只看一頁，位移超過一筆時可能誤判）見第 6 列補記 (a)。

已核可計畫／測試說明與程式的落差（不回改計畫）：Step 8 的「放在 `Sidebar.tsx:209-216` DEMO SCOPE 區塊之後」——該區塊已由後續單元移除，現位於「專案」之後、管理區之前，符合線框 §14；Step 3 的「`HierarchyFacade` 不改」——`hierarchy_facade.py:214` 已有 `is_approved` 拒絕（hierarchy-service review-01，2026-10-20）；Step 7 的 `fetchMemoryRecords` 多一個 `token` 參數，404 處置已由 Step 13 取代；`unit-test-instructions.md` 寫後端 7 案、e2e 10＋3 案，實為 9 案與 18 案（E11–E13 與修補輪撞號，spec 以 `MB6-` 註解區分）；測試說明的本機指令用 `python3` 與裸 `npx playwright`，預設 reporter 會寫出 `frontend/pw-report.json` 與 `junit.xml`。

候選問題（未修，交審查判定）：member-pages-ui 的兩種形狀在本單元不適用（`/memory` 無路由參數，`/me` 失敗有 `memory-page-identity-error`；本單元無 dialog，`DeleteConfirmRow` 為就地 `role="group"`，有 Escape 取消與焦點歸還）。(1) 刪除送出期間確認列卸載、刪除入口 `disabled`，焦點掉到 `body`；成功時情節區只在被刪列位於目前頁時才移焦點。(2) Sidebar「我的記憶」的 `<nav>` 沒有 `aria-label`，旁邊「專案」的有，可能觸發 axe `landmark-unique`。

## 共用檔異動後的重新驗證與補審（計畫 §四之二）

<!-- 寫入時間：2026-10-31T00:20:35Z（date -u） -->

本輪**未改任何程式、測試、共用檔、`merge-blockers.md`、`unit-test-instructions.md` 或其他單元的檔**。寫入僅限本檔與計畫的勾選格；`traceability.json` 不需更新（無新案例、無追溯目標變動）。

### 一、共用檔重驗

比對基準：mtime 最新的收據 `reviewed-source-00c3990a7da5.tsv`（2026-10-25 23:12，20 列：1 列 manifest ＋ 19 個檔）。逐列 `shasum -a 256`：

| 結果 | 檔案 |
|---|---|
| **變動（1）** | `backend/services/memory_facade.py`（收據 `3f4c15e0…848b` → 現值 `df149529…b4e7`） |
| 逐位元相同（19） | `source-manifest.json`（manifest 列）、`hierarchy_facade.py`、`memory_errors.py`、`memory_router.py`、`tests/test_memory_pending_authz.py`、`App.tsx`、`Sidebar.tsx`、`components/memory/` 四檔、`memory/` 四檔、`MemoryPage.tsx`、`types/api.d.ts`、`tests/e2e/memory-page.spec.ts`、`openapi.json` |

`memory_facade.py` 的改動來源：收據版本與 `8cf948c`（本單元提交）逐位元相同（`git show 8cf948c:` 匯出後 `shasum` 為 `3f4c15e0…848b`）；其後唯一的提交是 `7a50a40`（2026-10-27，合併前必修清單各單元修正），工作樹無未提交改動。`git diff 8cf948c 7a50a40` 只有**一個 hunk**：`delete` 末段把 `memory_service.delete_with_audit(...)` 包進 `try/except MemoryNotFound`，取列後、刪除前被另一 session 刪掉時以原值重拋 `MemoryNotFound(memory_id) from None`（合併前必修第 22 項 (c)），現位於 `:412-420`。

| 本單元負責或引用的部分 | 現況（行號為現檔） | 判定 |
|---|---|---|
| 六個公開方法第一行呼叫 `_authorize_approved` | `write` `:246`→`:272`；`search` `:297`→`:315`；`list_records` `:339`→`:352`；`delete` `:364`→`:393`；`widen_scope` `:424`→`:435`；`list_audit_events` `:473`→`:492`（`def` 與呼叫之間只有 docstring） | 未碰。`widen_scope`／`list_audit_events` 的行號較前輪紀錄（`:429`、`:486`）各後移 6 行，正是 `delete` 那個 hunk 的淨增行數，內容不變 |
| `reason=pending` 拒絕日誌 | `REASON_PENDING = "pending"` `:109`；`_authorize_approved` `:184-202` 先 `log_denied(reason=REASON_PENDING, …)` `:197-201` 再 raise `MemoryForbidden(reason=REASON_PENDING, …)` `:202` | 未碰 |
| `delete` 先判定後取列 | `:393` 判定 → `:394` `parse_memory_id` → `:396` `get_record` | 未碰；新 hunk 在取列與擁有者判定**之後** |
| `[D1]`=A 的 404 收斂 | 不存在 `:401`、非擁有者 `:410` 皆 `MemoryNotFound(memory_id)`；新增的競態分支 `:420` 同樣以呼叫端原值重拋 `MemoryNotFound`、不寫 `reason=owner`、不寫稽核 | 未破壞，且把收斂延伸到「取列後被併發刪除」這個第三入口，與 `[D1]`=A 同向 |

結論：變動不觸及本單元負責或引用的任何部分。附帶：新分支 `:416-420` 目前沒有測試走到，已由 `merge-blockers.md` 第 33 列 (f)（memory-service R-09）登錄，非本單元承接。

### 二、回歸

| 項目 | 指令與條件 | 結果 |
|---|---|---|
| 後端三模組 | 以 `rsync` 複製 `backend/`（排除 `.venv`、`__pycache__`、`.hypothesis`、`.env`）與 repo 根的 `schema_rbac.sql`、`schema.sql`、`openapi.json` 到 scratchpad；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<副本>/backend backend/.venv/bin/python -B -P`，於直譯器內 `os.chdir(<副本>/backend)` 後執行 `unittest -v tests.test_memory_pending_authz tests.test_memory_authz tests.test_memory_contract`（不以 `cd &&` 串接，故改在直譯器內切換目錄，效果與計畫指令相同） | `Ran 43 tests in 1.272s` / `OK`（pending_authz 9、authz 23、contract 11）；`C3` 綠 |
| OpenAPI 漂移（Step 6 證據） | 同一副本、同一直譯器，`dump_openapi.py --check` | `規格檔與後端程式碼一致。` |
| ESLint | 以 ESLint Node API（`cache:false`、`fix:false`，cwd 設為 `frontend/`）檢查本單元 12 檔：`MemoryPage.tsx`、`components/memory/` 四檔、`memory/` 四檔、`App.tsx`、`Sidebar.tsx`、`tests/e2e/memory-page.spec.ts` | `files=12 errors=0 warnings=0` |
| Playwright 收集（Step 2 證據） | `frontend/node_modules/.bin/playwright test --config <abs>/playwright.config.ts --list --reporter=list memory-page.spec.ts` | `Total: 18 tests in 1 file`；名稱與前輪一致 |
| e2e 是否重跑 | **不重跑**。理由：spec 與全部前端檔自收據後逐位元相同；`memory-page.spec.ts` 全部以 `page.route()` 攔截 `/api/memory/*`，不接觸後端，唯一變動的 `memory_facade.py` 不在其執行路徑上 | 沿用前輪 18/18 |
| repo 汙染檢查 | `find backend frontend -newer <本輪起點標記> -not -path "*/node_modules/*" -not -path "*/.venv/*"` | 無輸出（未留下 `.pyc`、`.hypothesis/`、報表檔） |

### 三、review-03 R-01..R-08 逐項現況

| ID | 現況查證 | 處置 |
|---|---|---|
| R-01 | 仍成立：`unit-test-instructions.md` 在 `8cf948c`→`c6a40f9` 間 +12 行（§四之三 `:90-100`），工作樹另 +2 行（`:52` 現況註記）；E11–E13 只出現在該檔 `:96-98`，spec 註解為 `MB6-E11`（`:889`）／`MB6-E12`（`:923`）／`MB6-E13`（`:956`），`traceability.json:173`、`:299` 用 `MB6-` | 已就地更正「重新查驗與合併前必修第 6 項」§六 第 2 列並附編號對照（該表下方標註） |
| R-02 | 仍成立：`MemoryZone.tsx:226-228` 註解只寫往前位移；判定為 id 比對 `:235` | 紀錄已就地補記（§五 下方）；程式註解需改程式 → 已知限制 L1 |
| R-03 | 仍成立：spec 的 `MB6-` 三案（`:899`、`:934`、`:966`）無「DELETE 在途時翻頁」情境；`rowPage` 由 `:364` 綁定、`:233` 使用 | 已就地補記「未被測試鎖住」；補 e2e 需改測試 → 已知限制 L2 |
| R-04 | 仍成立：`MB6-E13` 以 `stub.getHook` 回 500（`:973`），規格註解 `@api GET /api/memory/records -> 500`（`:963`）；spec 全檔無 `route.abort` | 改 `route.abort()` 需改測試 → 已知限制 L3 |
| R-05 | 仍成立（本輪前）：§二 第一點與 §六 第一列旁無標註 | 已就地加兩則標註（原文保留） |
| R-06 | 仍成立：`MemoryZone.tsx:253-256` 語意／程序區刪除完成後無條件 `headingRef.current?.focus()`；情節區有 `:266` 的 `rowPage === currentPage` 條件 | 記為已知取捨（DELETE 在途時間短、影響小）；修正需改程式 → 已知限制 L4 |
| R-07 | 仍成立：`MemoryItem.tsx:86` `setItemState('deleting')` 使確認列卸載、入口 `disabled`，此間焦點落在 `body`；成功由區塊移焦點、失敗經 `:71-74` effect 回到刪除鍵 | 記為已知取捨（最終落點正確）；修正需改程式 → 已知限制 L5 |
| R-08 | 仍成立：`Sidebar.tsx:247` 的 `<nav className="space-y-1 px-2">` 無 `aria-label`；`:129`（入口）、`:233`（專案）有；`:162`、`:218`、`:279` 另三個既有無標籤 `<nav>` | 需改程式 → 已知限制 L6 |

### 四、需 conductor 併入 `merge-blockers.md` 的已知限制

| # | 來源 | 內容 | 類型 | 與第 6 列的關係 |
|---|---|---|---|---|
| L1 | R-02 | `MemoryZone.tsx:226-228` 的已接受風險註解補上「往後」位移超過探測列 `limit=21` | 程式註解 | **已涵蓋**：第 6 列「審查後補記」(a) |
| L2 | R-03 | 補 e2e：DELETE 延遲、期間翻頁、404 後斷言重讀的 offset 為原頁（鎖住 `rowPage` 的選擇） | 測試缺口 | **已涵蓋**：第 6 列 (b)，已交 `build-and-test`／`tcms-test-cases` 斟酌 |
| L3 | R-04 | `MB6-E13` 改以 `route.abort()` 模擬重讀失敗，消除 `tcms_validate` WARN | 測試調整 | **已涵蓋**：第 6 列 (c) |
| L4 | R-06 | 語意／程序區刪除完成後只在焦點仍在該列內或在 `body` 時才移到區標題 | 無障礙（Minor） | **未涵蓋**，需新增 |
| L5 | R-07 | `deleting` 期間讓該列（`li`）暫時接焦點，避免焦點落在 `body` | 無障礙（Minor） | **未涵蓋**，需新增 |
| L6 | R-08 | `Sidebar.tsx:247` 的 `<nav>` 加 `aria-label="我的記憶"` | 無障礙（Minor，axe best-practice `landmark-unique`，`a11y.spec.ts` 的 WCAG 標籤集合不執行，閘門不會紅） | **未涵蓋**，需新增 |

R-01、R-05 已由本輪紀錄處置，不需併入（第 6 列 (d) 的紀錄面缺口由本輪結清）。

### 五、勾選重設

基準：前一輪（「重做」節）17 格全勾的紀錄，以及本計畫 §四之二 新增的 5 格（共 22 格）。逐格判定：

| 格 | 判定依據 | 勾 |
|---|---|---|
| Step 1 | `memory/`、`components/memory/` 八檔逐位元相同 | 是 |
| Step 2 | 本輪重驗：後端執行器 43 OK、Playwright 收集 18 案（「spec 不存在時回 0」因 spec 已存在不可重現，同前輪） | 是 |
| Step 3 | 唯一變動的 `memory_facade.py` 已逐項重驗（§一），`hierarchy_facade.py`、`memory_errors.py` 逐位元相同 | 是 |
| Step 4 | 測試檔逐位元相同，本輪重跑 43 OK | 是 |
| Step 5 | `memory_router.py`、`openapi.json`、`api.d.ts` 逐位元相同 | 是 |
| Step 6 | 本輪重跑 `dump_openapi.py --check` 一致；`api.d.ts` 與 `openapi.json` 皆未變，`check:types` 的兩個輸入不變 | 是 |
| Step 7、8 | 前端檔逐位元相同 | 是 |
| Step 9 | 本輪重跑 ESLint 0／0；建置輸入逐位元相同 | 是 |
| Step 10 | spec 與前端逐位元相同，e2e 不受後端改動影響（§二） | 是 |
| Step 11 | 本輪重跑兩支 validator（見下） | 是 |
| Step 12 | 本檔本輪更新；`source-manifest.json` 逐位元相同；`traceability.json` 未變且無需更新 | 是 |
| §四之一 Step 13、限制、測試、本機實跑 | 對應前端檔與 spec 逐位元相同 | 是 |
| §四之一 回填 | `merge-blockers.md:15` 第 6 列處置存在；`source-manifest.json`、`traceability.json`（`MB-6` 條目於 `:296`，註記於 `:299`）存在 | 是 |
| §四之二 五格 | 本節一至五 | 是 |

機械計數（勾選後執行）：`grep -c -E "^\s*- \[x\]" code-generation-plan.md` → **22**；`grep -c -E "^\s*- \[ \]" code-generation-plan.md` → **0**。另以 `git diff --numstat` 對 HEAD 比對計畫檔為 `10 0`（只多了 §四之二 的 10 行，無任何既有行被改動），證明本輪對計畫只動了勾選字元。不成立而維持未勾的格：無。

### 六、收尾檢查

| 指令 | 結果 |
|---|---|
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |

（兩支在本節寫入前、寫入後各跑一次，皆通過。）

## 合併前必修第 35 列（計畫 §四之三，2026-11-07T23:21:04Z）

來源：`construction/functional-design/merge-blockers.md` 第 35 列（review-03 R-06、R-07、R-08 與 review-04 新發現；即本檔前一節的已知限制 L4–L6）。本輪開工於 `2026-11-07T23:06:06Z`（`date -u`）。

### 一、改動（Step 14–16）

| Step | 檔案與行號（現檔） | 內容 |
|---|---|---|
| 14 (a) | `frontend/src/components/memory/MemoryZone.tsx:82-91`（新增 `focusIsOnRowOrLost`）、`:264-271`（`handleRemoved` 非情節區分支） | 語意區、程序區刪除完成後，只在 `document.activeElement` 為 null／`body`，或其 `closest('li')` 的 `data-testid` 等於 `memory-item-<被刪 id>` 時，才把焦點移到區標題；否則不搶焦點。判定在 `handleRemoved` 內、`setItems` commit 之前執行，此刻被刪的列仍在 DOM，故 `closest('li')` 可判定。情節區分支（`rowPage === currentPage`）不變 |
| 15 (b) | `frontend/src/components/memory/MemoryItem.tsx:77-88`（`rowRef` ＋ effect）、`:119`（`ref={rowRef}`）、`:122`（`tabIndex={isDeleting ? -1 : undefined}`） | 進入 `deleting` 後的 effect 中，若焦點已遺失（確認鍵卸載而落到 body）或仍在本列內，就 `focus()` 該 `li`。失敗時沿用既有 `restoreFocusToEntry` effect 把焦點還給刪除鍵（`tabIndex` 隨之移除）；成功時焦點在被刪列內，Step 14 的條件成立 → 移到區標題。`aria-disabled`、樣式不變 |
| 16 (c) | 查證，不改程式 | `Sidebar.tsx:248` 的 `<nav className="space-y-1 px-2" aria-label="我的記憶">` 由 **brain-infra** 計畫 A10（第 35 列 (c)、第 40 列）修改（工作樹未提交，`git diff --numstat` 為 `2 1`），由 `frontend/tests/e2e/sidebar-landmarks.spec.ts:70` 的 `Sidebar landmarks › memory nav landmark is named` 鎖住（該檔目前為未追蹤檔，屬 brain-infra）。已有斷言，故**不**在 `memory-page.spec.ts` 另補案 |

**Step 14 與 15 的時序協調**：按確認 → `deleting` commit（確認鍵卸載，焦點落到 body）→ Step 15 effect 把焦點移到該 `li` → 使用者若在 DELETE 在途時移開焦點，焦點即不在該列 → DELETE 完成時 `handleRemoved` 依 Step 14 判定。成功分支中焦點仍在 `li`（`closest('li')` 即本身）→ 移到區標題，故 Step 15 不會讓 Step 14 誤判為「使用者已移開」。以 e2e MB35-b 第三步實測：完成後語意區 `h2` 取得焦點。

### 二、測試（Step 17）

`frontend/tests/e2e/memory-page.spec.ts`，`describe` 仍為 `U15 memory page`、既有 18 案名稱未改，新增 4 案（皆附 `@purpose`／`@given`／`@step`／`@pass`／`@story`／`@api`／`@ui`／`@note`）：

| 編號 | 行 | 案名 |
|---|---|---|
| MB35-a1 | `:1003` | `after a semantic delete with focus left on the row, focus moves to the zone heading` |
| MB35-a2 | `:1028` | `a semantic delete that completes after focus moved elsewhere does not steal focus` |
| MB35-a3 | `:1062` | `a procedural delete that completes after focus moved elsewhere does not steal focus` |
| MB35-b | `:1096` | `while a delete is in flight, focus stays on the deleting row instead of the body` |

延遲一律用既有 `gate()`＋`deleteHook`，不用 `waitForTimeout`。

### 三、突變驗證（Step 18，只在 scratchpad 副本）

副本：`rsync` `frontend/`（排除 `node_modules`、`dist`、`test-results`、報表檔）到 scratchpad 的 `mpu-copy/frontend/`，`node_modules` 以 `cp -cR`（APFS 複製，非 symlink、不連網）帶入；`npm run build` 後 `vite preview --host 127.0.0.1 --port 4318`。repo 內被測檔未做任何突變。

| 突變 | 內容 | 結果 |
|---|---|---|
| 基準 | 未改 | 22 passed |
| M1 | `MemoryZone.tsx:269` 改回無條件 `headingRef.current?.focus()`（另以 `void focusIsOnRowOrLost;` 保持引用，否則 `tsc` 的 TS6133 使建置失敗、preview 仍服務舊產物——第一次嘗試即因此誤得 22 綠，已作廢重做） | **2 failed**：MB35-a2、MB35-a3（`toBeFocused` 失敗）；其餘 20 綠 |
| M2 | `MemoryItem.tsx` 的 `row.focus()` 判斷式改為 `void active;` | **1 failed**：MB35-b（`Expected "memory-item-1"`、`Received "body"`） |
| M3（附加） | `MemoryZone.tsx:269` 改為從不移焦點 | **2 failed**：MB35-a1、MB35-b（最後一步的區標題焦點） |
| 還原 | 兩檔以備份還原，與 repo 現檔 `shasum -a 256` 相同 | 22 passed |

計畫列的「拿掉 `aria-label` → 新案紅」不適用：本單元未新增 (c) 的案例；brain-infra 的 `sidebar-landmarks.spec.ts` 檔頭自記 M1／M2 突變（結果記於 brain-infra 的 `code-summary.md`）。

### 四、回歸（Step 19）

| 項目 | 結果 |
|---|---|
| `npm run lint`（repo 內 `frontend/`） | `0 errors, 2 warnings`（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344`，皆 `exhaustive-deps`、非本單元檔） |
| `npx tsc -b` | 無輸出（通過）；`.tsbuildinfo` 落在 `node_modules/.tmp/`（`.gitignore` 涵蓋） |
| `npm run build` | 通過（chunk 大小警告為既存）；`dist/` 為 `.gitignore` 涵蓋 |
| `npm run check:types` | `API 型別檔與規格檔一致。`（暫存目錄在系統 tmp，非 repo） |
| e2e `memory-page.spec.ts` | `vite preview --host 127.0.0.1 --port 4317` ＋ `BASE_URL`，`--reporter=list`、`--output` 指向 scratchpad：**22 passed**（既有 18 ＋ 新增 4）；跑完已關閉 preview |
| `a11y.spec.ts` 記憶頁相關 ＋ `sidebar-landmarks.spec.ts` | 同一 preview，`--grep`：`U17 a11y gate › 02 我的記憶頁`、`06 專案詳情記憶摘要籤`、`Sidebar landmarks` 兩案，**4 passed** |
| 後端三模組（副本） | scratchpad 實體副本（排除 `.venv`、`__pycache__`、`.hypothesis`、`.env`，附 repo 根 `schema_rbac.sql`、`schema.sql`、`openapi.json`），`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=<副本>/backend`、`HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/mpu-hyp`、`backend/.venv/bin/python -B`：`Ran 43 tests` / `OK` |
| OpenAPI 漂移（副本） | `dump_openapi.py --check` → `規格檔與後端程式碼一致。` |
| repo 汙染 | `find backend frontend -newer <開工標記>`（排除 `node_modules`、`.venv`、`frontend/dist`）只列出本輪三個改動檔；無新 `__pycache__`／`.hypothesis`。`frontend/junit.xml`、`pw-report.json`、`test-results/` 為本輪之前既存（mtime 早於開工標記），本輪未寫入 |

### 五、共用檔重驗（Step 20）

以最新收據 `reviewed-source-68dd09b8b313.tsv`（2026-10-31）逐檔 `shasum -a 256`：19 檔中 **10 檔變動**、9 檔相同（`test_memory_pending_authz.py`、`App.tsx`、`DeleteConfirmRow.tsx`、`EpisodicPager.tsx`、`memory/` 四檔、`MemoryPage.tsx`）；manifest 雜湊 `be134e17…177c` 相同。10 檔的 HEAD 版本皆與收據相同，變動全為**工作樹未提交改動**：

| 檔 | 來源 | 是否碰到本單元負責或引用的部分 |
|---|---|---|
| `MemoryZone.tsx`、`MemoryItem.tsx`、`memory-page.spec.ts` | 本輪 | 本單元自改（見一、二） |
| `Sidebar.tsx` | brain-infra A10 | 只在 `:247-248` 加 (c) 的註解與 `aria-label`；`sidebar-memory-link`、`showMemory` 判定未動 |
| `memory_facade.py` | 其他單元（第 33 列 (a)(b)(c)(e)、第 48 列） | 未碰：六個公開方法第一行仍為 `_authorize_approved`（`write` `:288`、`search` `:338`、`list_records` `:377`、`delete` `:418`、`widen_scope` `:460`、`list_audit_events` `:520`）；`REASON_PENDING` `:125`；`delete` 仍先判定 `:418` 後 `parse_memory_id` `:419`、`get_record` `:421`。附帶觀察（範圍外，僅記錄）：新增的公開方法 `count_references_to_user` 不經 `_authorize_approved`，其 docstring 寫明只回筆數、唯一呼叫端由 `require_story_action("J3a","edit")` 把關 |
| `hierarchy_facade.py` | 其他單元（第 25 列） | 未碰 `Principal`／`mint_principal`／`is_approved`；只新增 `HierarchyProjectAdminRequired` 與兩個刪除方法的 `project_admin` 參數 |
| `memory_errors.py` | 其他單元（第 33 列 (b)、第 48 列） | 基底類別更名 `MemoryError`→`MemoryServiceError`、新增 `MemoryStorageUnavailable`；`MemoryForbidden(reason=…)` 不變 |
| `memory_router.py` | 其他單元（第 48 列） | `DELETE` 的 `responses` 仍含 `FORBIDDEN_RESPONSE`（`:347`），`openapi.json` 該路由回應碼為 `204/403/404/422/503` |
| `openapi.json`、`api.d.ts` | 其他單元（第 33、48 列） | 只增 `maxLength`、503 描述；上方副本 `--check` 與 `check:types` 皆一致 |

結論：其他單元的改動不觸及本單元負責或引用的部分；後端三模組以含這些改動的工作樹副本重跑 43 OK。

### 六、勾選重設

開工時計畫的 30 格**全部是未勾**（`grep -c` 為 0／30，前一輪勾好的 22 格在 Request Changes 後被重設；`git show HEAD:` 版本為 17 格已勾）。逐格判定：

| 格 | 依據 | 勾 |
|---|---|---|
| Step 1 | 兩個目錄存在；`memory/` 四檔與收據相同，`components/memory/` 兩檔相同、兩檔本輪重驗 | 是 |
| Step 2 | 本輪重驗：後端 43 OK、Playwright 22 案實跑 | 是 |
| Step 3、4 | §五：facade 變動未碰本單元部分；副本 43 OK | 是 |
| Step 5、6 | `DELETE` 403 仍宣告；副本 `--check` 一致；`check:types` 一致 | 是 |
| Step 7 | `memory/` 四檔與收據相同 | 是 |
| Step 8 | `MemoryPage.tsx`、`App.tsx` 相同；`Sidebar.tsx` 他單元只加 `aria-label`；元件本輪改動並以 22 案重驗 | 是 |
| Step 9 | lint 0 errors、build 通過；本單元 9 個前端檔對 `localStorage`／`sessionStorage`／`IndexedDB`／`dangerouslySetInnerHTML` 的 `grep -c` 皆 0 | 是 |
| Step 10 | 22/22 | 是 |
| Step 11 | 兩支 validator 本輪通過（見七） | 是 |
| Step 12 | 本檔本輪 append；`source-manifest.json` 已涵蓋全部本輪改動檔，不需改（改了反而使 manifest 雜湊無故變動）；`traceability.json` 加 `MB-35` | 是 |
| §四之一 五格 | `memoryApi.ts` 與收據相同；`MemoryZone.tsx` 的 `deleteRecord` 本輪未動，MB6-E11–E13 本輪實跑綠；`merge-blockers.md` 第 6 列處置仍在 | 是 |
| §四之二 五格 | 該輪紀錄（本檔前一節）原文仍在；其結論由本節五、四重新確認 | 是 |
| §四之三 Step 14–21 | 本節一至七 | 是 |

機械計數（勾選後執行）：`grep -c -E "^\s*- \[x\]" code-generation-plan.md` → **30**；`grep -c -E "^\s*- \[ \]" code-generation-plan.md` → **0**。勾選以 `perl` 只替換行首 `- [ ]`，事後把 `[x]` 換回 `[ ]` 與勾選前備份 `diff` 為零差異，證明計畫內文未改。不成立而維持未勾的格：無。

### 七、收尾（Step 21）

| 項目 | 結果 |
|---|---|
| `source-manifest.json` | 不改（已含 `frontend/src/components/memory/` 與 `frontend/tests/e2e/memory-page.spec.ts`） |
| `traceability.json` | 新增 `upstream_ids` 的 `MB-35` 與對應 `coverage` 列；`json.load` 通過 |
| `merge-blockers.md` 第 35 列 | 處置欄以 Edit 就地補記（原文保留），結論為「待重審 memory-page-ui」 |
| `python3 -B scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| `python3 -B scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |

（兩支在本節寫入前、寫入後各跑一次。）

### 八、範圍外觀察（只記錄，不擴大）

- `frontend/tests/e2e/a11y.spec.ts:77` 的註解仍寫「我的記憶的 `<nav>` 無 aria-label」，在 brain-infra 補上 `aria-label` 後已過期；該檔為 brain-infra／a11y-gate 的工作樹改動，非本單元。
- `sidebar-landmarks.spec.ts` 為未追蹤檔：第 35 列 (c) 的鎖定依賴 brain-infra 的那批改動一起提交。
- `MemoryFacade.count_references_to_user` 不經 `_authorize_approved`（見五），由其他單元以理由記載。

## 整站重跑後的勾選回復（2026-11-08T15:43:25Z）

- 背景：2026-11-08T06:40:14Z 使用者決定重跑整個 code-generation 階段（整站關卡因審查收據失效卡死，唯一出路）。引擎把本計畫勾選全部重設為未勾。
- 依據：以 Python `hashlib` 重算上一次審查留下、與現況最吻合的收據 `reviewed-source-75c064902e47.tsv`：19 同、0 變。本輪 `REVIEW_REQUESTED` 當下引擎另會產生一份新收據，以那份為準。既有勾選依 HEAD 版回復（差異僅勾選字元）。
- 現況（實算）：30 勾／0 未勾。
