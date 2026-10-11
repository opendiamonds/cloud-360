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
