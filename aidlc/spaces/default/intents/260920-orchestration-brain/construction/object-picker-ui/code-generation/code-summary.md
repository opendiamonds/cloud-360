# Code Summary — `object-picker-ui`（U16，`kind: ui`）

<!-- Stage: code-generation（Construction 3.5）· Unit: object-picker-ui · Record: 260920-orchestration-brain -->

> 撰寫時間 2026-10-18T08:16:16Z（`date -u` 取值）。依核可的 `code-generation-plan.md`（14 步，全部勾選）與 Testing Contract（`test-after`、`standard`）執行。
> 綁定 `functional-spec-corrections.md`（F-01–F-08）、`nfr-requirements-corrections.md`（N-01–N-07）、`nfr-design-corrections.md`（D-01–D-07）；衝突時照附錄。
> 未 commit、未 push、未改 `.claude/`。後端、`deploy/`、`.github/`、`package.json`、`package-lock.json`、`ws-contract.json`、`playwright.config.ts` 本單元零變更。

## 一、交付檔案

| 檔案 | 動作 | 內容 |
|---|---|---|
| `frontend/src/brain/objectPickerModel.ts` | 新 | 純函式：`isOwnedByMe`、`rowKey`、`currentRowKey`、`targetIdsForProject`、`targetIdsForSystem`、`normalize`（NFKC＋trim＋小寫）、`filterGroups`（子字串比對） |
| `frontend/src/brain/objectPickerData.ts` | 新 | 純抓取：`fetchProjects`、`fetchSystems`（包 `listProjects`／`listSystems`，零 state、零主控台） |
| `frontend/src/components/brain/ObjectPicker.tsx` | 新 | dialog、焦點陷阱、Escape、方向鍵、搜尋、選單內播報區、衍生 `identity`、同步 ref 登記簿、展開／補抓、`switchError`、`reloadKey` |
| `frontend/src/components/brain/ObjectPickerGroup.tsx` | 新 | 專案群組：專案列、展開鈕、系統清單四態、非擁有者說明、「+ 新增系統」 |
| `frontend/src/components/brain/ObjectPickerCreateForm.tsx` | 新 | 單欄建立表單（`useRef` 單發鎖、只經 `objectCreateAction`）；`frontend-components.md` 的 `ObjectCreateForm` 改名以落入 lint 集合 |
| `frontend/tests/e2e/object-picker.spec.ts` | 新 | `describe('U16 object picker')`，26 個 test |
| `frontend/src/components/brain/ContextBar.tsx` | 改（**`U14` 的檔**） | 見 §二之一 |
| `frontend/eslint.config.js` | 改（**共用設定**） | 見 §二之二 |
| `frontend/tests/e2e/a11y.spec.ts` | 改（**`U17` 的檔**） | 見 §二之三 |

## 二、三個重開檔的逐點改動

### 二之一、`ContextBar.tsx`（`OPEN-OP16-4`）

1. 匯入 `useCallback`／`useEffect`／`useRef` 與 `ObjectPicker`、`PickerPlacement` 型別；檔內新增常數 `PICKER_WIDTH = 384`。
2. 檔頭註解第 20 行「本單元不渲染」改寫為指向 `U16`／`ObjectPicker.tsx` 的事實陳述（含斷線處置摘要）。
3. 新 state：`pickerOpen`、`pickerAnchor`、`prevStatus`；新 ref：`sectionRef`、`switchRef`、`wasVisibleRef`。
4. 衍生 `pickerVisible = pickerOpen && status === 'ready'`；以「依前值調整 state」在 `status` 離開 `ready` 時 `setPickerOpen(false)`（D-05）。
5. 一個 effect：選單原本可見、因斷線而不可見時，焦點移到 `<section>`、`announce('')` 後以 `setTimeout(…, 0)` 播報「連線中斷，已關閉作業對象選單」。**計時器不在 cleanup 清除**（斷線後 status 會連續變化，清除會吞掉播報）。
6. `togglePicker`（點擊當下量測鈕的座標）與 `closePicker`（清 `pickerOpen`、焦點回鈕）。
7. `<section>` 加 `ref`、`tabIndex={-1}`、`focus:outline-none`。
8. 名稱節點之後、共享徽章之前，`status === 'ready'` 時渲染「切換對象」鈕（`brain-context-switch-object`，`aria-haspopup="dialog"`、`aria-expanded`）與 `ObjectPicker`。
9. **不動**：五態判定、`brain-context-name-*`、`brain-context-none`、共享徽章與切換、展開的 `<dl>`。無新增 prop、三個頁面檔未改。

### 二之二、`eslint.config.js`（`N-03`、`D-06`）

- `defineConfig([...])` 之前新增常數 `OBJECT_PICKER_FILES`、`OBJECT_PICKER_RESTRICTIONS`（六條選擇器，含 D-06 的 `window.<storage>`）、`OBJECT_PICKER_CREATE_IMPORT`。
- 陣列**末端**新增一個區塊（`files: OBJECT_PICKER_FILES`）：`no-console`、`no-restricted-globals`（四種儲存）、`no-restricted-imports`（兩個相對深度的 `projectsApi` 禁匯入 `createProject`／`createSystem`）、`no-restricted-syntax`（展開 `WS_SUBPROTOCOL_RESTRICTIONS` ＋ 選單六條）。
- 既有兩個區塊與既有常數**一行不動**（以 `diff` 對照動工前備份，`export default` 之後只有新增的 23 行）。

### 二之三、`a11y.spec.ts`（`OPN-23`、`N-06`）

- 新增 `stagePicker()`（已連線入口頁＋`K2` view／edit＋樁化三個專案的 `/api/hierarchy`，含一個他人擁有的專案；可選 POST 回 409）與 `openPicker()`。
- `SCANS` 新增 `pickerDefault`（`21-object-picker-default`）、`pickerCreateError`（`22-object-picker-create-error`），兩者 `include` 皆為 `[data-testid="brain-object-picker"]`，沿用既有 `scan()`／`isolate()`／`ready()`。
- 新增 test `21 切換對象選單預設態`、`22 切換對象選單建立錯誤態`（放在兩個基準清單 test 之前，維持「過期檢查必須最後」的檔內順序）。
- **附帶改動（揭露）**：既有註解與「基準清單沒有過期條目」的規格註解中的計數「19」改為「21」（5 行）。該 test 的程式以 `ALL_SCANS` 動態計數，不需改；改註解是為了讓 TCMS 描述與事實一致。test 名稱未改。
- `a11y-baseline.json` 未改（`entries` 仍為空陣列，雜湊前後相同）。

## 三、帶入事項的處置結果

| 事項 | 結果 |
|---|---|
| `OPEN-OP16-4` | 如 §二之一；既有 brain e2e 全綠（§六） |
| `OPN-23` | 如 §二之三；`U17` 原 22 ＋ 新 2 共 24 個 test 全綠 |
| `N-03`／`D-06` lint 區塊 | 如 §二之二；`npm run lint` 0 errors／2 warnings（動工前同為 0／2） |
| 選單檔案集合命名 | 三個元件皆以 `ObjectPicker` 開頭 |
| `D-05` 重複字串 | `announce('')` ＋ `setTimeout(…, 0)`；e2e「連續兩次斷線」該句累計 2 次 |
| `AC9.2.3` | 讀為 Deferred（F-01），畫面面已交付（無權限不渲染入口、403 文案）；字面裁決交 `G-2` |
| F-01 的 404 二擇一 | 選**不可達＋其他文案**（N-04）：前端擁有者條件使「他人專案下建系統」不可達；被移出的建立者情境以 e2e 驗證顯示「建立系統失敗，請稍後再試」、名稱保留（`G-6`） |

## 四、`D-05` 斷線寫法的 lint 實證

`ContextBar.tsx` 採「依前值調整 state」（渲染中 `if (prevStatus !== status) { setPrevStatus(status); if (status !== 'ready' && pickerOpen) setPickerOpen(false); }`）。
實跑 `npx eslint src/components/brain src/brain`（`eslint-plugin-react-hooks@7.1.1` flat recommended，含 error 級 `set-state-in-render`／`set-state-in-effect`／`refs`）：**0 problems**；全專案 `npm run lint` 0 errors。備案（卸載清理）依 D-05 已刪除、未實作。

## 五、突變驗證（M1–M16，`security-design.md` §六 ＋ D-02／D-07／D-01）

方法：腳本逐一以字串替換套用 → 確認檔案內容與備份不同 → lint 類跑 `npx eslint <檔>`、e2e 類 `npm run build` 後以 `-g` 跑對應 test → 從備份還原並以 `cmp` 確認位元相同。17 道（M16 拆 a／b）**全部紅、全部還原**。完工後 7 個被突變的檔再次逐一 `cmp` 皆與備份相同，並 grep 確認無殘留（`console.`、`sessionStorage`、`dangerously`、`RegExp(`、`as never`、`|| true` 皆 0 命中於程式碼）。

| # | 套用內容 | 紅燈位置 |
|---|---|---|
| M1 | `ObjectPicker.tsx`：`{canEdit && (` → `{(canEdit \|\| true) && (`（底部新增專案） | e2e `無建立權限者看不到建立入口且空清單只有說明`：`brain-object-create-project` Expected 0 / Received 1 |
| M2 | `canCreateSystem={owned && canEdit}` → `g.project.owner_user_id !== userId && canEdit` | e2e `非擁有者專案照列但不可選且無新增系統入口`：`create-system-5` Expected 0 / Received 1 |
| M3 | `ObjectPickerGroup.tsx` 專案名改 `dangerouslySetInnerHTML` | lint（OPN-13 選擇器）＋ e2e `惡意名稱以純文字呈現`（文字為空，名稱被解析成 HTML） |
| M4 | `filterGroups` 專案名比對改 `new RegExp(q).test(...)` | lint（OPN-14）＋ e2e `搜尋特殊字元不拋例外`（`no-match` 未出現） |
| M5 | 專案清單 `.then` 加 `console.log(projects)` | lint `no-console` ＋ e2e `選單一輪不輸出主控台且不寫儲存`（新增主控台訊息 ≠ 0） |
| M6 | `onSearch` 加 `sessionStorage.setItem('picker', value)` | lint `no-restricted-globals` ＋ e2e 同上（儲存鍵集合多 1） |
| M7 | `ObjectPicker.tsx` 加 `import { createProject } from '../../projects/projectsApi'` | lint `no-restricted-imports` |
| M8 | `targetIdsForSystem` 的 `projectId` 改 `system.project_id as never` | e2e `選系統送出字串三層 id 且回推前脈絡列不變`（payload `projectId` 為數字） |
| M9 | 表單單發鎖 `if (submittingRef.current) return;` → `if (pending) return;` | e2e `同一任務內連續送出只發一個建立請求`：POST Expected 1 / Received 2（**實際看到紅燈**，D-02 的同任務 `el.click()` 兩次） |
| M10 | 刪除 `ensureSystems` 的 `loading/loaded` 早退 | e2e `三十個專案時請求數有上界且搜尋只補抓一次`：收起再展開後請求 Expected 2 / Received 3 |
| M11 | 刪除 `ContextBar` 的 `setPickerOpen(false)`（依前值調整） | e2e `斷線時選單關閉焦點移到脈絡列且重連不復現`：重連後選單 Expected 0 / Received 1 |
| M12 | `ensureSystems` 改讀 state：`systemsByProject.get(pid)?.status` | e2e `補抓佇列中展開同一群組只抓一次`：Expected 1 / Received 2 |
| M13 | 刪除 `backfillStartedRef` 條件（每次輸入都補抓） | e2e `三十個專案時請求數有上界且搜尋只補抓一次`：並行數 Expected ≤ 4 / Received 8（見 §八偏離 2） |
| M14 | 身分 effect 刪除 `refreshTriedRef` 防重 | e2e `身分未決時只補呼叫一次 refreshMe（缺 id）`：Expected 1 / Received 195（情境 b 因 `refreshMe` 拋錯不觸發重渲染而綠，情境 a 已足以抓到） |
| M15 | `normalize` 拿掉 `NFKC` | e2e `全形搜尋命中半形名稱`：專案 1 不可見 |
| M16a | 斷線時不移焦點 | e2e `斷線時…`：`activeElement` Expected `brain-context-bar` / Received null |
| M16b | 斷線時不播報 | e2e `斷線時…`：`__announcements` 中無該句 |

**lint 規則逐條實證（N-03，`OPN-25` 的 lint 部分）**：在 `objectPickerModel.ts`／`objectPickerData.ts` 逐行加入違規後 `npx eslint` 皆報 error 並還原（`cmp` 確認）：`localStorage`、`window.localStorage`、`indexedDB`、`caches`、`el.innerHTML =`、`el.outerHTML =`、`RegExp('x')`、`new WebSocket(...)`、`console.info`、`../projects/projectsApi` 匯入 `createSystem`——10 項全紅。

## 六、實跑的指令與結果

前端以 `npm run build` ＋ `npx vite preview --port 4173 --strictPort`（背景）服務；結束時 `pkill -f "vite preview --port 4173"`，`pgrep` 確認已停止。

| 指令 | 結果 |
|---|---|
| Step 2 基準：`BASE_URL=http://localhost:4173 npx playwright test tests/e2e/entry-page.spec.ts --reporter=line`（動工前） | 49 passed |
| `… tests/e2e/object-picker.spec.ts --reporter=list` | **26 passed / 0 failed** |
| `… tests/e2e/a11y.spec.ts --reporter=list`（整檔） | **24 passed / 0 failed**（原 22 ＋ 新 2），新兩點基準以外違規 0 |
| `… tests/e2e/entry-page.spec.ts --reporter=list` | **49 passed / 0 failed** |
| `… tests/e2e/memory-page.spec.ts project-pages.spec.ts member-pages.spec.ts` | **48 passed / 0 failed** |
| `… tests/e2e/entry-page-live.spec.ts` | **5 failed（環境，無法在本機執行）**：該檔對 `docker-compose.test.yml` 的真實 stack 以 seed 帳號 `admin` 登入；本機無 Docker、無後端，五案皆在登入後的 `toHaveURL(/\/$/)` 失敗。與本單元改動無關，但**本輪未取得該檔的綠燈證據**，需在 CI 的 `ui-regression` 確認 |
| `npm run lint` | 0 errors、2 warnings（`AssessmentPage.tsx`、`WorkspacePage.tsx` 的 `exhaustive-deps`，動工前即存在；warning 數未增） |
| `npm run build`（含 `tsc -b`） | 通過 |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/object-picker.spec.ts` | 26/26 通過（初跑 2 個 ERROR「預期結果無具體證據」，已補 backtick 與具體值後重跑通過；僅改註解） |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/a11y.spec.ts` | 24/24 通過 |

## 七、`N-05` 比較基準（動工前 2026-10-18T04:06:09Z／完工時）

| 項 | 動工前 | 完工時 |
|---|---|---|
| `git hash-object ws-contract.json` | `fbe262e97d64592a2277a58d64256f96e1c5e8a2` | `fbe262e97d64592a2277a58d64256f96e1c5e8a2` |
| `jq -c '.dependencies, .devDependencies \| keys' frontend/package.json` | `["html2canvas","jspdf","react","react-dom","react-router-dom"]`／19 個 devDependencies（`@axe-core/playwright` … `vite`） | 相同 |
| `git hash-object frontend/tests/e2e/a11y-baseline.json` | `7f19696e7be79af4fbab91db7075dbcfa734f62e` | `7f19696e7be79af4fbab91db7075dbcfa734f62e` |

`git diff --stat -- backend deploy .github` 有 14 個檔的變更，**全部是動工前工作樹已存在的其他單元未提交變更**（會話開始時的 git status 即列出 `backend/…` 與 `.github/workflows/deploy.yml`）；本單元未觸碰。

## 八、偏離計畫之處與理由

1. **選單以 `fixed` 定位而非 `absolute`**：`/assessment` 的脈絡列外層是 `overflow-hidden rounded-2xl`（`AssessmentPage.tsx:1238`），`absolute` 會被裁切而看不到。改為點擊當下（事件處理函式內，不在 effect 內 setState）量測鈕的 `getBoundingClientRect()`，以 `top`／CSS 變數 `--picker-left` 定位；`md:` 斷點語意保留（`left-4 right-4` 全寬 → `md:left-(--picker-left) md:right-auto md:w-96`）。殘留：選單開啟期間若外層捲動，選單不跟隨（不關閉）；視窗縮放時不重算。
2. **M13 的紅燈改由並行上限斷言承接**：D-07 預期「再輸入 10 字元後請求數由 31 增加」；但 D-01 的同步登記簿讓重複補抓不會發出重複請求，該斷言對 M13 恆綠。實際可觀察的退化是「每次輸入另起一個佇列、並行數超過 4」（違反 N-02 第 3 點的同時最多 4 個），故 e2e 加入 `maxInFlightSystems ≤ 4` 斷言，並把第一次輸入改為連續兩個字（第二個字落在補抓進行中）。請求數 31 的斷言保留。
3. **補抓的工作在執行時才檢查登記簿**：`D-01` 寫「發出請求之前同步寫入 loading」，本實作照做；另把補抓佇列的工作設計為 `queue.enqueue(() => ensureSystems(pid))`（入列時不寫登記簿），使 M12（改讀 state）能真的紅——若入列時就寫登記簿，M12 會因展開處理函式讀到重渲染後的 state 而恆綠。
4. **新增 testid**（計畫未列）：`brain-object-identity-retry`、`brain-object-list`、`brain-object-loading`、`brain-object-empty`、`brain-object-no-match`、`brain-object-error`、`brain-object-group-{id}`、`brain-object-group-loading-{id}`／`-error-{id}`／`-empty-{id}`、`brain-object-create-form-{kind}`。
5. **重試鈕的焦點處置**（計畫未明列）：群組重試、專案清單重試、身分重試的按鈕會在重試開始時被移除，焦點會落到 body 而使 Escape 失效（e2e 實際踩到）；改為重試時把焦點移到穩定控件（該群組展開鈕／搜尋框）。
6. **選單內播報區另播「已載入 N 個專案」與「N 個符合的專案」**（W1 第 7 步、`BR13.4` 的結果數），依 F-04 寫在選單內播報區。
7. **`BR14.5` 的 `setWorkTarget` 回 false**：依 D-03 不重抓清單，顯示「已建立，但目前無法切換」並收起表單；新建的物件此時不在清單上，要到下次開啟才可選。
8. **`switchError` 情境的構造**：以 `page.evaluate` 改寫頁面 `WebSocket.OPEN`，使 `sendFrame` 判定未開啟而連線狀態仍為 ready（routeWebSocket 會替換頁面的 WebSocket 類別，覆寫原型 `readyState` 無效）。
9. **e2e 不寫 `@api`**（全部攔截）；`@ui` 只用 `/`、`/workspace`、`/assessment`；`@story` 用 `US9.2`（`a11y.spec.ts` 兩個新掃描點亦同，既有掃描點為 `N-9`）。

## 九、`OPN-26` 測試底線（`team.md` A／B／C）

A 不適用（不改 `role_permissions`）；B 不適用（不新增或修改 HTTP 端點）；**C 適用**，對應 e2e：`object-picker.spec.ts` 全部 26 案（新畫面與資料形狀）及 `a11y.spec.ts` 的 `21 切換對象選單預設態`、`22 切換對象選單建立錯誤態`。

## 十、ADR-0006 四面向與 PBT

沿用 `security-design.md` §七、§八：IAM 適用（呈現層；伺服器仍是授權點，前端判定只決定是否顯示必然被拒的控件）；Encryption、Network exposure、Audit logging 不適用（零持久化、零新端點、零新環境變數；不繞過 `U7` 的建立稽核）；PBT 不適用（三個純函式以 e2e 例子驗證，M2／M4／M8／M15 證明它們被斷言到）。

## 十一、未完成或交下游的事項

- `entry-page-live.spec.ts` 本機無法執行（§六），待 CI。
- `OPN-25` 的 `automation-test-plan.md` 屬 `tcms-test-cases` stage；本檔 §五已記錄 M1–M16 與 lint 逐條結果，供該 stage 轉錄。
- 螢幕閱讀器實際朗讀、手機實機操作交 `build-and-test`／`tcms-test-cases`。

## 十二、關卡事項（原文照列）

| # | 事項 | 來源 |
|---|---|---|
| G-1 | `CreateConfirmCard` 不實作（範圍縮減）與其下游文件 | `OPEN-OP16-1`、F-07 |
| G-2 | `AC9.2.3` 字面與 `U7` 實作矛盾，請裁決改 AC 或改 `U7` | F-01 |
| G-3 | 刪除使用者路徑不存在，是否另開 intent | D-4、F-08 |
| G-4 | 新建架構圖的系統歸屬無端點 | D-5 |
| G-5 | 受邀成員看得到但選不了自己的非擁有專案 | `OPEN-OP16-5`（即 `OPEN-PP23-6` ③） |
| G-6 | 「建立者在選單開啟後被移出」時，建立系統顯示「請稍後再試」會誘使無效重試；本站判可接受，若不接受須重開 `U23` 的 `objectCreateAction` | `N-04` |
